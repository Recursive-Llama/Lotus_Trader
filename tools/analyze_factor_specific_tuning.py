#!/usr/bin/env python3
"""
Factor-Specific Tuning Analysis - What should we actually learn?
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from datetime import datetime, timedelta
import json

def extract_median(d):
    """Extract median from dict with max/min/median or return value directly"""
    if isinstance(d, dict):
        return d.get('median', d.get('max', d.get('min', None)))
    return d

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("FACTOR-SPECIFIC TUNING ANALYSIS")
    print("=" * 80)
    
    # Get events
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    res = sb.table("pattern_episode_events")\
        .select("*")\
        .neq("outcome", "null")\
        .gte("timestamp", cutoff)\
        .execute()
    
    s1_events = [e for e in res.data if 'S1.entry' in e.get('pattern_key', '')]
    
    # Group by outcome
    misses = []  # Skipped but would have succeeded
    dodges = []  # Skipped and correctly avoided failure
    wins = []    # Acted and succeeded
    failures = [] # Acted and failed
    
    for e in s1_events:
        decision = e.get('decision')
        outcome = e.get('outcome')
        factors = e.get('factors', {})
        
        if decision == 'skipped' and outcome == 'success':
            misses.append(factors)
        elif decision == 'skipped' and outcome == 'failure':
            dodges.append(factors)
        elif decision == 'acted' and outcome == 'success':
            wins.append(factors)
        elif decision == 'acted' and outcome == 'failure':
            failures.append(factors)
    
    print(f"\n📊 Current Situation:")
    print(f"  Misses: {len(misses)} (skipped successes)")
    print(f"  Dodges: {len(dodges)} (skipped failures) - 91.8% dodge rate ✅")
    print(f"  Wins: {len(wins)} (acted successes)")
    print(f"  Failures: {len(failures)} (acted failures)")
    
    # Extract key factors
    def get_factor_median(group, factor_key):
        values = []
        for f in group:
            if isinstance(f, dict):
                val = f.get(factor_key)
                if val is not None:
                    median = extract_median(val)
                    if median is not None:
                        values.append(float(median))
        return sum(values) / len(values) if values else None
    
    print(f"\n{'='*80}")
    print("FACTOR-SPECIFIC ANALYSIS")
    print(f"{'='*80}")
    
    # Analyze TS scores
    print(f"\n🎯 TS Score Analysis:")
    miss_ts = get_factor_median(misses, 'ts_score')
    dodge_ts = get_factor_median(dodges, 'ts_score')
    win_ts = get_factor_median(wins, 'ts_score')
    fail_ts = get_factor_median(failures, 'ts_score')
    
    print(f"  Misses (skipped successes): TS = {miss_ts:.3f}" if miss_ts else "  Misses: No TS data")
    print(f"  Dodges (skipped failures): TS = {dodge_ts:.3f}" if dodge_ts else "  Dodges: No TS data")
    print(f"  Wins (acted successes): TS = {win_ts:.3f}" if win_ts else "  Wins: No TS data")
    print(f"  Failures (acted failures): TS = {fail_ts:.3f}" if fail_ts else "  Failures: No TS data")
    
    if miss_ts and dodge_ts:
        print(f"\n  💡 Insight: Misses have TS={miss_ts:.3f} vs Dodges TS={dodge_ts:.3f}")
        if miss_ts > dodge_ts:
            print(f"    → Misses have HIGHER TS than dodges!")
            print(f"    → This suggests TS threshold might be OK, but something else blocked us")
        elif miss_ts < dodge_ts:
            print(f"    → Misses have LOWER TS than dodges")
            print(f"    → This suggests TS threshold might be too high (we're skipping good opportunities)")
        else:
            print(f"    → Same TS - need to look at other factors")
    
    # Analyze Halo Distance
    print(f"\n🎯 Halo Distance Analysis:")
    miss_halo = get_factor_median(misses, 'halo_distance')
    dodge_halo = get_factor_median(dodges, 'halo_distance')
    win_halo = get_factor_median(wins, 'halo_distance')
    fail_halo = get_factor_median(failures, 'halo_distance')
    
    print(f"  Misses: halo_distance = {miss_halo:.3f}" if miss_halo else "  Misses: No halo data")
    print(f"  Dodges: halo_distance = {dodge_halo:.3f}" if dodge_halo else "  Dodges: No halo data")
    print(f"  Wins: halo_distance = {win_halo:.3f}" if win_halo else "  Wins: No halo data")
    print(f"  Failures: halo_distance = {fail_halo:.3f}" if fail_halo else "  Failures: No halo data")
    
    if miss_halo and dodge_halo:
        print(f"\n  💡 Insight: Misses have halo={miss_halo:.3f} vs Dodges halo={dodge_halo:.3f}")
        if miss_halo < dodge_halo:
            print(f"    → Misses have SMALLER halo distance (closer to EMA)")
            print(f"    → This suggests halo might be too tight (we're skipping close opportunities)")
        elif miss_halo > dodge_halo:
            print(f"    → Misses have LARGER halo distance (further from EMA)")
            print(f"    → This suggests halo might be OK, but TS or slope blocked us")
    
    if fail_halo and win_halo:
        print(f"\n  💡 Insight: Failures have halo={fail_halo:.3f} vs Wins halo={win_halo:.3f}")
        if fail_halo < win_halo:
            print(f"    → Failures have SMALLER halo (closer to EMA)")
            print(f"    → This suggests we might be acting too early (halo too loose)")
        elif fail_halo > win_halo:
            print(f"    → Failures have LARGER halo (further from EMA)")
            print(f"    → This suggests we might be acting too late (halo too tight)")
    
    # Analyze Slope
    print(f"\n🎯 Slope Analysis:")
    miss_slope = get_factor_median(misses, 'ema60_slope')
    dodge_slope = get_factor_median(dodges, 'ema60_slope')
    win_slope = get_factor_median(wins, 'ema60_slope')
    fail_slope = get_factor_median(failures, 'ema60_slope')
    
    if miss_slope:
        print(f"  Misses: ema60_slope = {miss_slope:.6f}")
    if dodge_slope:
        print(f"  Dodges: ema60_slope = {dodge_slope:.6f}")
    if win_slope:
        print(f"  Wins: ema60_slope = {win_slope:.6f}")
    if fail_slope:
        print(f"  Failures: ema60_slope = {fail_slope:.6f}")
    
    # What we're missing
    print(f"\n{'='*80}")
    print("WHAT WE'RE MISSING")
    print(f"{'='*80}")
    print("""
    ❌ We don't capture:
    1. ts_min - The actual threshold we compared against
    2. halo_max - The actual halo limit we compared against
    3. slope_ok - Whether slope gate passed
    4. entry_zone_ok - Whether all gates passed
    
    Without this, we can't tell:
    - Which specific gate blocked us (TS? halo? slope?)
    - What the threshold was at decision time
    - Why we skipped vs why we acted
    
    Current system just says "pressure = +3, loosen everything"
    But we should say:
    - "Misses had TS=0.5 but threshold was 0.6 → lower TS threshold"
    - "Failures had halo=0.4 but we acted → tighten halo"
    """)
    
    # What the system SHOULD do
    print(f"\n{'='*80}")
    print("WHAT THE SYSTEM SHOULD DO")
    print(f"{'='*80}")
    print("""
    1. Factor-Specific Pressure:
       - TS Pressure = Compare misses TS vs threshold, failures TS vs threshold
       - Halo Pressure = Compare misses halo vs limit, failures halo vs limit
       - Slope Pressure = Compare misses slope vs requirement, failures slope vs requirement
    
    2. Targeted Adjustments:
       - Only adjust TS if TS is the problem
       - Only adjust halo if halo is the problem
       - Don't blanket-adjust everything
    
    3. Consider Overall Performance:
       - Dodge rate is 91.8% - that's GOOD
       - We're correctly avoiding 89 failures
       - Don't loosen too much and break this
    
    4. Impact Analysis:
       - If we lower TS threshold by X, how many misses would we catch?
       - How many extra failures would we take?
       - Is the trade-off worth it?
    """)
    
    # Simulate impact
    print(f"\n{'='*80}")
    print("IMPACT SIMULATION")
    print(f"{'='*80}")
    
    print(f"\n  Current: 8 misses, 5 failures, 89 dodges (91.8% dodge rate)")
    print(f"\n  If we loosen thresholds (current system would do this):")
    print(f"    - Might catch some of the 8 misses")
    print(f"    - But might also take some of the 89 dodges (which would fail)")
    print(f"    - Risk: Break the 91.8% dodge rate")
    
    print(f"\n  If we do factor-specific tuning:")
    print(f"    - Analyze which gate blocked the 8 misses")
    print(f"    - Only adjust that specific gate")
    print(f"    - Preserve the 91.8% dodge rate on other gates")

if __name__ == "__main__":
    main()

