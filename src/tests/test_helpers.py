"""
Test helper functions for PM v4 Uptrend testing

Provides:
- wait_for_condition: Polling helper for async operations
- Database query helpers
- Assertion helpers
"""

import time
import sys
import os
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def wait_for_condition(
    condition: Callable[[], bool],
    timeout: int = 30,
    poll_interval: int = 5,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for condition to be true, polling at intervals.
    
    Used for flow tests where we need to wait for async operations
    (e.g., position creation, backfill completion, execution confirmation).
    
    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds (default: 30)
        poll_interval: Time between polls in seconds (default: 5)
        error_message: Error message if timeout exceeded
        
    Returns:
        True if condition met within timeout
        
    Raises:
        TimeoutError: If condition not met within timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(poll_interval)
    raise TimeoutError(error_message)


def get_positions_by_token(
    supabase_manager,
    token_contract: str,
    chain: str,
    created_after: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Query positions by token contract and chain.
    
    Args:
        supabase_manager: Supabase manager instance
        token_contract: Token contract address
        chain: Chain name (solana, ethereum, etc.)
        created_after: Optional datetime to filter by creation time
        
    Returns:
        List of position dictionaries
    """
    query = (
        supabase_manager.client.table("lowcap_positions")
        .select("*")
        .eq("token_contract", token_contract)
        .eq("token_chain", chain)
    )
    
    if created_after:
        query = query.gte("created_at", created_after.isoformat())
    
    result = query.execute()
    return result.data if result.data else []


def get_strand_by_id(
    supabase_manager,
    strand_id: str
) -> Optional[Dict[str, Any]]:
    """
    Query strand by ID.
    
    Args:
        supabase_manager: Supabase manager instance
        strand_id: Strand ID
        
    Returns:
        Strand dictionary or None if not found
    """
    result = (
        supabase_manager.client.table("ad_strands")
        .select("*")
        .eq("id", strand_id)
        .limit(1)
        .execute()
    )
    
    return result.data[0] if result.data else None


def get_coefficient(
    supabase_manager,
    module: str,
    scope: str,
    name: str,
    key: str
) -> Optional[Dict[str, Any]]:
    """
    Query learning coefficient.
    
    Args:
        supabase_manager: Supabase manager instance
        module: Module identifier (e.g., 'dm')
        scope: Scope (e.g., 'lever', 'interaction', 'timeframe')
        name: Lever name (e.g., 'curator', 'chain')
        key: Bucket value or hashed combination
        
    Returns:
        Coefficient dictionary or None if not found
    """
    result = (
        supabase_manager.client.table("learning_coefficients")
        .select("*")
        .eq("module", module)
        .eq("scope", scope)
        .eq("name", name)
        .eq("key", key)
        .limit(1)
        .execute()
    )
    
    return result.data[0] if result.data else None


def get_global_rr_baseline(
    supabase_manager
) -> Optional[Dict[str, Any]]:
    """
    Query global R/R baseline from learning_configs.
    
    Args:
        supabase_manager: Supabase manager instance
        
    Returns:
        Global R/R dictionary with rr_short, rr_long, n, or None if not found
    """
    result = (
        supabase_manager.client.table("learning_configs")
        .select("config_data")
        .eq("module_id", "decision_maker")
        .limit(1)
        .execute()
    )
    
    if result.data and len(result.data) > 0:
        config_data = result.data[0].get("config_data", {})
        return config_data.get("global_rr")
    
    return None


def assert_allocation_splits(
    positions: List[Dict[str, Any]],
    total_allocation_usd: float,
    expected_splits: Dict[str, float],
    tolerance: float = 0.01
) -> None:
    """
    Assert that position allocation splits match expected values.
    
    Args:
        positions: List of position dictionaries
        total_allocation_usd: Total allocation USD
        expected_splits: Expected splits by timeframe (e.g., {'1m': 0.05, '15m': 0.125, ...})
        tolerance: Tolerance for floating point comparison (default: 0.01)
        
    Raises:
        AssertionError: If splits don't match expected values
    """
    # Verify splits sum to 1.0
    assert abs(sum(expected_splits.values()) - 1.0) < tolerance, \
        f"Expected splits must sum to 1.0, got {sum(expected_splits.values())}"
    
    # Verify each position's allocation
    for position in positions:
        timeframe = position.get("timeframe")
        alloc_cap_usd = float(position.get("alloc_cap_usd", 0))
        expected_pct = expected_splits.get(timeframe, 0)
        expected_alloc = total_allocation_usd * expected_pct
        
        assert abs(alloc_cap_usd - expected_alloc) < tolerance, \
            f"Position {timeframe} allocation mismatch: expected ${expected_alloc:.2f}, got ${alloc_cap_usd:.2f}"
    
    # Verify total matches
    total_alloc = sum(float(p.get("alloc_cap_usd", 0)) for p in positions)
    assert abs(total_alloc - total_allocation_usd) < tolerance, \
        f"Total allocation mismatch: expected ${total_allocation_usd:.2f}, got ${total_alloc:.2f}"


def assert_coefficient_bounds(
    coefficient: Dict[str, Any],
    weight_min: float = 0.5,
    weight_max: float = 2.0
) -> None:
    """
    Assert that coefficient weight is within bounds.
    
    Args:
        coefficient: Coefficient dictionary
        weight_min: Minimum weight (default: 0.5)
        weight_max: Maximum weight (default: 2.0)
        
    Raises:
        AssertionError: If weight is out of bounds
    """
    weight = coefficient.get("weight")
    assert weight is not None, "Coefficient weight is None"
    assert weight_min <= weight <= weight_max, \
        f"Coefficient weight {weight} is out of bounds [{weight_min}, {weight_max}]"

