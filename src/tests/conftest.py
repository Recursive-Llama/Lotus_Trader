"""
Pytest configuration and fixtures for PM v4 Uptrend testing

Provides:
- Database fixtures with transaction rollback
- Test data fixtures (tokens, curators, etc.)
- Test helpers
"""

import pytest
import os
from typing import Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Supabase manager
import sys
import os
# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.supabase_manager import SupabaseManager


@pytest.fixture(scope="function")
def test_db():
    """
    Create test database connection with transaction rollback.
    
    Each test gets a fresh transaction that is rolled back after the test.
    This ensures test isolation.
    """
    # Get test database URL from environment
    test_db_url = os.getenv('TEST_SUPABASE_URL', os.getenv('SUPABASE_URL'))
    test_db_key = os.getenv('TEST_SUPABASE_KEY', os.getenv('SUPABASE_KEY'))
    
    if not test_db_url or not test_db_key:
        pytest.skip("Test database credentials not configured")
    
    # Create Supabase manager for test database
    supabase_manager = SupabaseManager()
    
    # Start transaction (if supported by Supabase client)
    # Note: Supabase Python client doesn't support transactions directly
    # We'll use a test database that can be reset between runs
    yield supabase_manager
    
    # Cleanup (transaction rollback would happen here if supported)
    # For now, we rely on test database isolation


@pytest.fixture
def test_token():
    """
    Test token fixture - POLYTALE on Solana
    
    Source: token_registry_backup.json
    """
    return {
        "contract": "B8bFLQUZg9exegB1RWV9D7eRsQw1EjyfKU22jf1fpump",
        "chain": "solana",
        "ticker": "POLYTALE",
        "name": "POLYTALE",
        # Expected buckets (verify at test time - may vary)
        "expected_mcap_bucket": "100k-500k",  # Verify at test time
        "expected_vol_bucket": "50k-200k",     # Verify at test time
        "expected_age_bucket": "<7d",          # Verify at test time
        "min_ohlc_bars": 350  # Minimum bars required for 1h timeframe
    }


@pytest.fixture
def test_curator():
    """
    Test curator fixture - 0xdetweiler
    
    Source: twitter_curators.yaml
    """
    return {
        "id": "0xdetweiler",
        "chain_counts": {"solana": 5, "base": 3},  # Verify at test time - may vary
        "test_tweet_format": "Check out $POLYTALE on Solana! 🚀"
    }


@pytest.fixture
def test_wallet():
    """
    Test wallet configuration
    
    Note: Store actual wallet address and private key in test config, not in code
    """
    return {
        "address": os.getenv('TEST_WALLET_ADDRESS', ''),
        "private_key": os.getenv('TEST_WALLET_PRIVATE_KEY', ''),
        "chain": "solana",
        "initial_balance_usdc": 15.0,  # $15-25 USDC for testing
        "network": "mainnet"  # Mainnet for real execution testing
    }


@pytest.fixture
def test_signal_id():
    """
    Generate unique test signal ID for flow tests
    """
    return f"test_signal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"


@pytest.fixture
def empty_learning_system():
    """
    Fixture for cold start tests - ensures learning system has no data
    """
    return {
        "learning_coefficients": [],  # Empty
        "learning_configs": {}  # Empty
    }


@pytest.fixture
def mock_engine_payload_s1_buy():
    """
    Mock engine payload for S1 initial entry (buy_signal)
    
    Used in PM/Executor testing (Scenario 9)
    """
    return {
        "state": "S1",
        "buy_signal": True,
        "buy_flag": False,
        "first_dip_buy_flag": False,
        "trim_flag": False,
        "emergency_exit": False,
        "exit_position": False,
        "scores": {
            "ts": 0.65,
            "ts_with_boost": 0.70,
            "sr_boost": 0.05
        },
        "price": 0.0001,
        "diagnostics": {
            "buy_check": {
                "entry_zone_ok": True,
                "slope_ok": True,
                "ts_ok": True,
                "ema60_slope": 0.003,
                "ema144_slope": 0.001
            }
        }
    }


@pytest.fixture
def mock_engine_payload_s3_emergency_exit():
    """
    Mock engine payload for S3 emergency exit
    
    Used in PM/Executor testing and position closure testing
    """
    return {
        "state": "S3",
        "buy_signal": False,
        "buy_flag": False,
        "trim_flag": False,
        "emergency_exit": True,
        "exit_position": False,
        "scores": {
            "ox": 0.50,
            "dx": 0.40,
            "edx": 0.60,
            "ts": 0.45
        }
    }

