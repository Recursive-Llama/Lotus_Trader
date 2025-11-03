#!/usr/bin/env python3
"""Diagnose BLOXWAP backtest issues"""

import json
from datetime import datetime

data = json.load(open('backtester/v1/backtest_results_v2_BLOXWAP_1762034400.json'))

print('=== BLOXWAP Backtest Diagnostics ===\n')

# 1. Find S1 breakout
s1_entry = next((r for r in data if r.get('state') == 'S1'), None)
if s1_entry:
    levels = s1_entry.get('levels', {})
    ts = s1_entry.get('analysis_ts', '')
    breakout_px = float(levels.get('current_price', 0) or 0)
    base_sr = float(levels.get('base_sr_level', 0) or 0)
    flipped = levels.get('flipped_sr_levels', [])
    
    print(f'1. S1 BREAKOUT INFO:')
    print(f'   Time: {ts}')
    print(f'   Breakout Price: {breakout_px:.10f}')
    print(f'   Base S/R Level: {base_sr:.10f}')
    if base_sr > 0:
        print(f'   Base S/R < Breakout?: {base_sr < breakout_px} (should be True)')
        print(f'   Distance from breakout: {((breakout_px - base_sr) / breakout_px * 100):.2f}%')
    print(f'   Flipped levels: {len(flipped)}')
    
    if flipped:
        print(f'\n   Flipped S/R Levels (should be between prev_close and breakout):')
        for j, fl in enumerate(flipped[:5]):
            level = fl.get('level', fl) if isinstance(fl, dict) else fl
            score = fl.get('score', 0) if isinstance(fl, dict) else 0
            print(f'     {j+1}. {level:.10f} (score: {score:.3f})')

# 2. Check all S/R levels being plotted
print(f'\n2. S/R LEVELS PLOTTED ON CHART:')
seen_prices = set()
sr_plot = []
for r in data:
    # S3 sr_context
    ctx = r.get('sr_context', {})
    if ctx.get('base_sr_level'):
        p = float(ctx['base_sr_level'])
        if p > 0 and p not in seen_prices:
            sr_plot.append({'p': p, 't': 'base', 's': 'S3', 'ts': r.get('analysis_ts', '')})
            seen_prices.add(p)
    for fl in ctx.get('flipped_sr_levels', []):
        price = float(fl.get('level', 0)) if isinstance(fl, dict) else float(fl)
        if price > 0 and price not in seen_prices:
            sr_plot.append({'p': price, 't': 'flipped', 's': 'S3', 'ts': r.get('analysis_ts', '')})
            seen_prices.add(price)
    
    # S2 levels
    lev = r.get('levels', {})
    if lev.get('base_sr_level'):
        p = float(lev['base_sr_level'])
        if p > 0 and p not in seen_prices:
            sr_plot.append({'p': p, 't': 'base', 's': 'S2', 'ts': r.get('analysis_ts', '')})
            seen_prices.add(p)
    for fl in lev.get('flipped_sr_levels', []):
        price = float(fl.get('level', 0)) if isinstance(fl, dict) else float(fl)
        if price > 0 and price not in seen_prices:
            sr_plot.append({'p': price, 't': 'flipped', 's': 'S2', 'ts': r.get('analysis_ts', '')})
            seen_prices.add(price)

base_levels = [s for s in sr_plot if s['t'] == 'base']
print(f'   Total base S/R levels (cyan): {len(base_levels)}')
for s in sorted(base_levels, key=lambda x: x['p']):
    is_above = f" (ABOVE breakout!)" if s1_entry and s['p'] > breakout_px else ""
    print(f"     {s['p']:.10f} from {s['s']}{is_above}")

print(f'\n   Total flipped S/R levels (blue): {len([s for s in sr_plot if s['t'] == 'flipped'])}')

# 3. Check buy signals
print(f'\n3. BUY SIGNALS:')
buy_signals = []
for i, r in enumerate(data):
    state = r.get('state', '')
    flags = r.get('flag', {}) or r.get('flags', {})
    uptrend_holding = bool(flags.get('uptrend_holding', False))
    
    if uptrend_holding:
        scores = r.get('scores', {})
        ti = float(scores.get('trend_integrity', 0) or 0)
        ts = float(scores.get('trend_strength', 0) or 0)
        buy_signals.append({
            'i': i,
            'state': state,
            'ts': r.get('analysis_ts', ''),
            'ti': ti,
            'ts_score': ts,
        })

print(f'   Total buy signals (uptrend_holding=True): {len(buy_signals)}')
for sig in buy_signals:
    print(f"     Index {sig['i']}: State={sig['state']} | {sig['ts']} | TI={sig['ti']:.3f} TS={sig['ts_score']:.3f}")

# 4. Check S2 window and why no buys
print(f'\n4. S2 WINDOW ANALYSIS:')
s2_entries = [(i, r) for i, r in enumerate(data) if r.get('state') == 'S2']
print(f'   Total S2 bars: {len(s2_entries)}')
for i, r in s2_entries:
    flags = r.get('flag', {}) or r.get('flags', {})
    scores = r.get('scores', {})
    uptrend_holding = bool(flags.get('uptrend_holding', False))
    ti = float(scores.get('trend_integrity', 0) or 0)
    ts = float(scores.get('trend_strength', 0) or 0)
    
    # Check thresholds (A=0.5, normal)
    tau_integrity = 0.60  # 0.80 - 0.40*0.5
    tau_strength = 0.575  # 0.75 - 0.35*0.5
    
    meets_ti = ti >= tau_integrity
    meets_ts = ts >= tau_strength
    meets_all = uptrend_holding and meets_ti and meets_ts
    
    print(f"     Bar {i} ({r.get('analysis_ts', '')}):")
    print(f"       uptrend_holding: {uptrend_holding}")
    print(f"       TI: {ti:.3f} >= {tau_integrity}? {meets_ti}")
    print(f"       TS: {ts:.3f} >= {tau_strength}? {meets_ts}")
    print(f"       → Buy signal? {meets_all}")

