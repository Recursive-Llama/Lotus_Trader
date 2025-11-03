#!/usr/bin/env python3
"""Check S1 breakout conditions at specific price levels"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from backtester.backtest_uptrend_v2 import SupabaseCtx, _build_ta_payload_from_rows, _filter_valid_bars, _forward_fill_prices

def check_s1_conditions(contract: str, chain: str, price_min: float, price_max: float):
    sbx = SupabaseCtx()
    
    print(f"=== S1 Breakout Conditions Check ===\n")
    print(f"Contract: {contract[:20]}...")
    print(f"Chain: {chain}")
    print(f"Price range: {price_min:.10f} - {price_max:.10f}\n")
    
    # Get all bars in the date range
    from datetime import timedelta
    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(days=14)
    
    rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, end_ts.isoformat(), limit=400)
    valid_rows = _filter_valid_bars(rows_1h)
    
    # Find bars in price range OR specific dates
    bars_in_range = []
    for r in valid_rows:
        price = float(r.get("close_native", 0) or 0)
        ts = r.get("timestamp")
        # Also check for Nov 1 bars (S1 breakout day)
        ts_str = str(ts)
        is_nov1 = "2025-11-01" in ts_str
        if price_min <= price <= price_max or is_nov1:
            bars_in_range.append((ts, price, r))
    
    # Sort by timestamp
    bars_in_range.sort(key=lambda x: x[0])
    print(f"Found {len(bars_in_range)} bars in price range or Nov 1\n")
    
    # Check conditions for each bar - prioritize Nov 1 bars
    nov1_bars = [b for b in bars_in_range if "2025-11-01" in str(b[0])]
    if nov1_bars:
        print(f"=== NOV 1 BARS (S1 Breakout Day) ===\n")
        for ts_str, price, r in nov1_bars:
            # Get data up to this bar
            bar_ts = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
            rows_to_bar = sbx.fetch_ohlc_1h_lte(contract, chain, bar_ts.isoformat(), limit=400)
            valid_to_bar = _filter_valid_bars(rows_to_bar)
            
            if len(valid_to_bar) < 72:
                continue
            
            rows_filled = _forward_fill_prices(valid_to_bar)
            ta = _build_ta_payload_from_rows(rows_filled)
            
            if not ta:
                continue
            
            ema_slopes = ta.get("ema_slopes", {})
            seps = ta.get("separations", {})
            atr = ta.get("atr", {})
            vol = ta.get("volume", {})
            
            ema20_slope = float(ema_slopes.get("ema20_slope", 0) or 0)
            dsep_fast_5 = float(seps.get("dsep_fast_5", 0) or 0)
            atr_1h = float(atr.get("atr_1h", 0) or 0)
            atr_mean_20 = float(atr.get("atr_mean_20", atr_1h) or atr_1h)
            vo_cluster = bool(vol.get("vo_z_cluster_1h", False))
            
            cond1 = ema20_slope > 0.0
            cond2 = dsep_fast_5 > 0.0
            cond3 = atr_1h > atr_mean_20
            cond4 = vo_cluster
            
            all_met = cond1 and cond2 and cond3 and cond4
            
            print(f"Bar {str(ts_str)[:19]}: Price={price:.10f}")
            print(f"  1. ema20_slope > 0: {ema20_slope:.6f} {'✓' if cond1 else '✗'}")
            print(f"  2. dsep_fast_5 > 0: {dsep_fast_5:.6f} {'✓' if cond2 else '✗'}")
            print(f"  3. atr_1h > atr_mean_20: {atr_1h:.10f} > {atr_mean_20:.10f} {'✓' if cond3 else '✗'}")
            print(f"  4. vo_z_cluster_1h: {vo_cluster} {'✓' if cond4 else '✗'}")
            print(f"  → ALL MET? {'✓ YES' if all_met else '✗ NO'}\n")
    
    print(f"\n=== Other bars in price range (first 10) ===\n")
    other_bars = [b for b in bars_in_range if "2025-11-01" not in str(b[0])]
    for ts_str, price, r in other_bars[:10]:  # Check first 10
        # Get data up to this bar
        bar_ts = datetime.fromisoformat(str(ts_str).replace('Z', '+00:00'))
        rows_to_bar = sbx.fetch_ohlc_1h_lte(contract, chain, bar_ts.isoformat(), limit=400)
        valid_to_bar = _filter_valid_bars(rows_to_bar)
        
        if len(valid_to_bar) < 72:
            continue
        
        rows_filled = _forward_fill_prices(valid_to_bar)
        ta = _build_ta_payload_from_rows(rows_filled)
        
        if not ta:
            continue
        
        ema_slopes = ta.get("ema_slopes", {})
        seps = ta.get("separations", {})
        atr = ta.get("atr", {})
        vol = ta.get("volume", {})
        
        ema20_slope = float(ema_slopes.get("ema20_slope", 0) or 0)
        dsep_fast_5 = float(seps.get("dsep_fast_5", 0) or 0)
        atr_1h = float(atr.get("atr_1h", 0) or 0)
        atr_mean_20 = float(atr.get("atr_mean_20", atr_1h) or atr_1h)
        vo_cluster = bool(vol.get("vo_z_cluster_1h", False))
        
        cond1 = ema20_slope > 0.0
        cond2 = dsep_fast_5 > 0.0
        cond3 = atr_1h > atr_mean_20
        cond4 = vo_cluster
        
        all_met = cond1 and cond2 and cond3 and cond4
        
        print(f"Bar {str(ts_str)[:19]}: Price={price:.10f}")
        print(f"  1. ema20_slope > 0: {ema20_slope:.6f} {'✓' if cond1 else '✗'}")
        print(f"  2. dsep_fast_5 > 0: {dsep_fast_5:.6f} {'✓' if cond2 else '✗'}")
        print(f"  3. atr_1h > atr_mean_20: {atr_1h:.10f} > {atr_mean_20:.10f} {'✓' if cond3 else '✗'}")
        print(f"  4. vo_z_cluster_1h: {vo_cluster} {'✓' if cond4 else '✗'}")
        print(f"  → ALL MET? {'✓ YES' if all_met else '✗ NO'}\n")

if __name__ == "__main__":
    # Get from existing results
    import json
    data = json.load(open('backtester/v1/backtest_results_v2_BLOXWAP_1762034400.json'))
    contract = data[0].get('contract')
    chain = data[0].get('chain')
    check_s1_conditions(contract, chain, 0.000004, 0.000005)

