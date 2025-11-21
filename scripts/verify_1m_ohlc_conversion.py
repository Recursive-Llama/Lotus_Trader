#!/usr/bin/env python3
"""
Verification script for 1m OHLC conversion.

Tests the conversion logic:
- Open = Previous candle's close (or first price if no previous)
- Close = Current price
- High = max(open, close)
- Low = min(open, close)

Edge cases tested:
- First bar (no previous close)
- Sequential bars (previous close used as open)
- Price gaps (missing data)
- Price increases (high = close, low = open)
- Price decreases (high = open, low = close)
- Price unchanged (high = low = open = close)
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import (
    GenericOHLCRollup,
    OHLCBar,
    DataSource,
    Timeframe
)


def create_test_price_points() -> List[Dict[str, Any]]:
    """Create test price points for verification."""
    base_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    
    # Test case 1: Sequential bars with price increase
    # Bar 1: First bar (no previous close)
    # Bar 2: Price increases (open = prev close, close = higher)
    # Bar 3: Price decreases (open = prev close, close = lower)
    # Bar 4: Price unchanged (open = close = prev close)
    
    return [
        {
            'token_contract': 'test_token_1',
            'chain': 'solana',
            'timestamp': (base_time + timedelta(minutes=0)).isoformat(),
            'price_usd': 1.0,
            'price_native': 0.001,
            'volume': 100.0,
        },
        {
            'token_contract': 'test_token_1',
            'chain': 'solana',
            'timestamp': (base_time + timedelta(minutes=1)).isoformat(),
            'price_usd': 1.1,  # Price increased
            'price_native': 0.0011,
            'volume': 150.0,
        },
        {
            'token_contract': 'test_token_1',
            'chain': 'solana',
            'timestamp': (base_time + timedelta(minutes=2)).isoformat(),
            'price_usd': 1.05,  # Price decreased
            'price_native': 0.00105,
            'volume': 120.0,
        },
        {
            'token_contract': 'test_token_1',
            'chain': 'solana',
            'timestamp': (base_time + timedelta(minutes=3)).isoformat(),
            'price_usd': 1.05,  # Price unchanged
            'price_native': 0.00105,
            'volume': 80.0,
        },
        # Test case 2: Gap in data (missing minute)
        {
            'token_contract': 'test_token_1',
            'chain': 'solana',
            'timestamp': (base_time + timedelta(minutes=5)).isoformat(),  # Gap: missing minute 4
            'price_usd': 1.2,
            'price_native': 0.0012,
            'volume': 200.0,
        },
    ]


def verify_conversion_logic(ohlc_bars: List[OHLCBar], price_points: List[Dict[str, Any]]) -> bool:
    """Verify the conversion logic matches expected behavior."""
    print("\n=== Verification Results ===\n")
    
    all_passed = True
    
    # Test Case 1: First bar (no previous close)
    if len(ohlc_bars) > 0:
        bar1 = ohlc_bars[0]
        price1 = price_points[0]
        
        expected_open_usd = price1['price_usd']
        expected_close_usd = price1['price_usd']
        expected_high_usd = max(expected_open_usd, expected_close_usd)
        expected_low_usd = min(expected_open_usd, expected_close_usd)
        
        print(f"Test 1: First bar (no previous close)")
        print(f"  Expected: Open={expected_open_usd}, Close={expected_close_usd}, High={expected_high_usd}, Low={expected_low_usd}")
        print(f"  Actual:   Open={bar1.open_usd}, Close={bar1.close_usd}, High={bar1.high_usd}, Low={bar1.low_usd}")
        
        if (bar1.open_usd == expected_open_usd and 
            bar1.close_usd == expected_close_usd and
            bar1.high_usd == expected_high_usd and
            bar1.low_usd == expected_low_usd):
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    # Test Case 2: Sequential bar with price increase
    if len(ohlc_bars) > 1:
        bar1 = ohlc_bars[0]
        bar2 = ohlc_bars[1]
        price2 = price_points[1]
        
        expected_open_usd = bar1.close_usd  # Previous close
        expected_close_usd = price2['price_usd']
        expected_high_usd = max(expected_open_usd, expected_close_usd)
        expected_low_usd = min(expected_open_usd, expected_close_usd)
        
        print(f"\nTest 2: Sequential bar with price increase")
        print(f"  Previous bar close: {bar1.close_usd}")
        print(f"  Expected: Open={expected_open_usd}, Close={expected_close_usd}, High={expected_high_usd}, Low={expected_low_usd}")
        print(f"  Actual:   Open={bar2.open_usd}, Close={bar2.close_usd}, High={bar2.high_usd}, Low={bar2.low_usd}")
        
        if (bar2.open_usd == expected_open_usd and 
            bar2.close_usd == expected_close_usd and
            bar2.high_usd == expected_high_usd and
            bar2.low_usd == expected_low_usd):
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    # Test Case 3: Sequential bar with price decrease
    if len(ohlc_bars) > 2:
        bar2 = ohlc_bars[1]
        bar3 = ohlc_bars[2]
        price3 = price_points[2]
        
        expected_open_usd = bar2.close_usd  # Previous close
        expected_close_usd = price3['price_usd']
        expected_high_usd = max(expected_open_usd, expected_close_usd)
        expected_low_usd = min(expected_open_usd, expected_close_usd)
        
        print(f"\nTest 3: Sequential bar with price decrease")
        print(f"  Previous bar close: {bar2.close_usd}")
        print(f"  Expected: Open={expected_open_usd}, Close={expected_close_usd}, High={expected_high_usd}, Low={expected_low_usd}")
        print(f"  Actual:   Open={bar3.open_usd}, Close={bar3.close_usd}, High={bar3.high_usd}, Low={bar3.low_usd}")
        
        if (bar3.open_usd == expected_open_usd and 
            bar3.close_usd == expected_close_usd and
            bar3.high_usd == expected_high_usd and
            bar3.low_usd == expected_low_usd):
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    # Test Case 4: Price unchanged
    if len(ohlc_bars) > 3:
        bar3 = ohlc_bars[2]
        bar4 = ohlc_bars[3]
        price4 = price_points[3]
        
        expected_open_usd = bar3.close_usd  # Previous close
        expected_close_usd = price4['price_usd']
        expected_high_usd = max(expected_open_usd, expected_close_usd)
        expected_low_usd = min(expected_open_usd, expected_close_usd)
        
        print(f"\nTest 4: Price unchanged")
        print(f"  Previous bar close: {bar3.close_usd}")
        print(f"  Expected: Open={expected_open_usd}, Close={expected_close_usd}, High={expected_high_usd}, Low={expected_low_usd}")
        print(f"  Actual:   Open={bar4.open_usd}, Close={bar4.close_usd}, High={bar4.high_usd}, Low={bar4.low_usd}")
        
        if (bar4.open_usd == expected_open_usd and 
            bar4.close_usd == expected_close_usd and
            bar4.high_usd == expected_high_usd and
            bar4.low_usd == expected_low_usd):
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    # Test Case 5: Gap in data (missing minute)
    if len(ohlc_bars) > 4:
        bar4 = ohlc_bars[3]
        bar5 = ohlc_bars[4]
        price5 = price_points[4]
        
        # Even with a gap, open should be previous close
        expected_open_usd = bar4.close_usd  # Previous close (even with gap)
        expected_close_usd = price5['price_usd']
        expected_high_usd = max(expected_open_usd, expected_close_usd)
        expected_low_usd = min(expected_open_usd, expected_close_usd)
        
        print(f"\nTest 5: Gap in data (missing minute)")
        print(f"  Previous bar close: {bar4.close_usd}")
        print(f"  Gap: Missing minute 4, jumped to minute 5")
        print(f"  Expected: Open={expected_open_usd}, Close={expected_close_usd}, High={expected_high_usd}, Low={expected_low_usd}")
        print(f"  Actual:   Open={bar5.open_usd}, Close={bar5.close_usd}, High={bar5.high_usd}, Low={bar5.low_usd}")
        
        if (bar5.open_usd == expected_open_usd and 
            bar5.close_usd == expected_close_usd and
            bar5.high_usd == expected_high_usd and
            bar5.low_usd == expected_low_usd):
            print("  ✅ PASSED")
        else:
            print("  ❌ FAILED")
            all_passed = False
    
    # Test Case 6: Verify High >= Low always
    print(f"\nTest 6: High >= Low validation")
    all_valid = True
    for i, bar in enumerate(ohlc_bars):
        if bar.high_usd < bar.low_usd:
            print(f"  ❌ Bar {i}: High ({bar.high_usd}) < Low ({bar.low_usd})")
            all_valid = False
        if bar.high_native < bar.low_native:
            print(f"  ❌ Bar {i}: High native ({bar.high_native}) < Low native ({bar.low_native})")
            all_valid = False
    
    if all_valid:
        print("  ✅ PASSED: All bars have High >= Low")
    else:
        all_passed = False
    
    # Test Case 7: Verify Open and Close are within High/Low range
    print(f"\nTest 7: Open/Close within High/Low range")
    all_valid = True
    for i, bar in enumerate(ohlc_bars):
        if not (bar.low_usd <= bar.open_usd <= bar.high_usd):
            print(f"  ❌ Bar {i}: Open ({bar.open_usd}) not in range [Low={bar.low_usd}, High={bar.high_usd}]")
            all_valid = False
        if not (bar.low_usd <= bar.close_usd <= bar.high_usd):
            print(f"  ❌ Bar {i}: Close ({bar.close_usd}) not in range [Low={bar.low_usd}, High={bar.high_usd}]")
            all_valid = False
    
    if all_valid:
        print("  ✅ PASSED: All Open/Close values within High/Low range")
    else:
        all_passed = False
    
    return all_passed


def main():
    """Run verification tests."""
    print("=" * 60)
    print("1m OHLC Conversion Verification")
    print("=" * 60)
    
    # Create test data
    price_points = create_test_price_points()
    
    print(f"\nCreated {len(price_points)} test price points")
    print("\nTest data:")
    for i, point in enumerate(price_points):
        print(f"  {i+1}. {point['timestamp']}: ${point['price_usd']:.4f} (native: {point['price_native']:.6f})")
    
    # Create rollup instance
    rollup = GenericOHLCRollup()
    
    # Convert using the internal method
    ohlc_bars = rollup._convert_1m_to_ohlc(price_points)
    
    print(f"\nConverted to {len(ohlc_bars)} OHLC bars")
    print("\nOHLC bars:")
    for i, bar in enumerate(ohlc_bars):
        print(f"  {i+1}. {bar.timestamp.isoformat()}: O={bar.open_usd:.4f}, H={bar.high_usd:.4f}, L={bar.low_usd:.4f}, C={bar.close_usd:.4f}")
    
    # Verify conversion logic
    all_passed = verify_conversion_logic(ohlc_bars, price_points)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

