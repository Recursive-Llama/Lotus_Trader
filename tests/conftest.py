"""
Pytest configuration and shared fixtures for Lotus Trader tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import os
from pathlib import Path

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase_manager():
    """Mock Supabase manager for testing."""
    mock = Mock()
    mock.client = Mock()
    mock.client.table.return_value = Mock()
    return mock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock = AsyncMock()
    mock.chat.completions.create = AsyncMock()
    return mock


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        "symbol": "BTC-USD",
        "timestamp": "2024-01-01T00:00:00Z",
        "open": 50000.0,
        "high": 51000.0,
        "low": 49000.0,
        "close": 50500.0,
        "volume": 1000.0
    }


@pytest.fixture
def sample_strand_data():
    """Sample strand data for testing."""
    return {
        "kind": "pattern_detected",
        "module": "raw_data_intelligence",
        "symbol": "BTC-USD",
        "timeframe": "1m",
        "tags": ["volume_spike", "breakout"],
        "sig_sigma": 2.5,
        "sig_confidence": 0.85,
        "outcome_score": 0.0
    }
