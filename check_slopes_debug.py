#!/usr/bin/env python3
"""Quick debug: Check if slopes are being calculated for BREW around Oct 25-26."""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import datetime, timezone
from backtester.v3.code.backtest_uptrend_v3 import SupabaseCtx, _build_ta_payload_from_rows, _filter_valid_bars
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v3 import UptrendEngineV3

# Test around Oct 25-26
target_ts = datetime(2025, 10, 25, 6, 0, 0, tzinfo=timezone.utc)
contract = "2hXQn7nJbh2XFTxvtyKb5mKfnScuoiC1Sm8rnWydpump"
chain = "solana"

print(f"Checking slopes for {target_ts.isoformat()}")
print("=" * 60)

sbx = SupabaseCtx()
rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, target_ts.isoformat(), limit=400)
valid_rows = _filter_valid_bars(rows_1h)
print(f"Valid bars: {len(valid_rows)}/{len(rows_1h)}")

if len(valid_rows) >= 72:
    ta = _build_ta_payload_from_rows(rows_1h)
    if ta:
        slopes = ta.get("ema_slopes", {})
        ema = ta.get("ema", {})
        
        print(f"\nEMA Values (latest):")
        print(f"  EMA60: {ema.get('ema60_1h', 0):.8e}")
        print(f"  EMA144: {ema.get('ema144_1h', 0):.8e}")
        
        print(f"\nSlopes (%/bar):")
        print(f"  EMA60 slope: {slopes.get('ema60_slope', 0):.8f}")
        print(f"  EMA144 slope: {slopes.get('ema144_slope', 0):.8f}")
        
        ema60_slope = slopes.get('ema60_slope', 0.0)
        ema144_slope = slopes.get('ema144_slope', 0.0)
        slope_ok = (ema60_slope > 0.0) or (ema144_slope >= 0.0)
        
        print(f"\nSlope Check:")
        print(f"  EMA60 > 0? {ema60_slope > 0.0}")
        print(f"  EMA144 >= 0? {ema144_slope >= 0.0}")
        print(f"  slope_ok: {slope_ok}")
        
        # Now check if engine reads it
        features = {"ta": ta}
        engine = UptrendEngineV3()
        ta_read = engine._read_ta(features)
        slopes_read = ta_read.get("ema_slopes", {})
        
        print(f"\nEngine read back:")
        print(f"  EMA60 slope: {slopes_read.get('ema60_slope', 0):.8f}")
        print(f"  EMA144 slope: {slopes_read.get('ema144_slope', 0):.8f}")
        
        if slopes_read.get('ema60_slope') == slopes.get('ema60_slope'):
            print("  ✓ Slopes match!")
        else:
            print("  ✗ Slopes DON'T match!")
    else:
        print("TA build returned empty!")
else:
    print(f"Not enough bars (need 72, got {len(valid_rows)})")

