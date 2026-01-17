#!/usr/bin/env python3
"""
Analyze Tuning Factors - What specific thresholds caused misses vs failures?
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

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("ANALYZING TUNING FACTORS - WHAT CAUSED MISSES VS FAILURES?")
    print("=" * 80)
    
    # Get events with outcomes
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    res = sb.table("pattern_episode_events")\
        .select("*")\
        .neq("outcome", "null")\
        .gte("timestamp", cutoff)\
        .execute()
    
    events = res.data or []
    print(f"\n📊 Events with outcomes: {len(events)}")
    
    if not events:
        return
    
    # Focus on S1.entry pattern
    s1_events = [e for e in events if 'S1.entry' in e.get('pattern_key', '')]
    print(f"  S1.entry events: {len(s1_events)}")
    
    # Analyze factors
    print(f"\n{'='*80}")
    print("FACTOR ANALYSIS")
    print(f"{'='*80}")
    
    # Group by outcome and decision
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
    
    print(f"\n  Misses (skipped successes): {len(misses)}")
    print(f"  Dodges (skipped failures): {len(dodges)}")
    print(f"  Wins (acted successes): {len(wins)}")
    print(f"  Failures (acted failures): {len(failures)}")
    
    # Analyze which factors are present
    def analyze_factors(group, name):
        if not group:
            print(f"\n  {name}: No data")
            return
        
        # Get all factor keys
        all_keys = set()
        for f in group:
            if isinstance(f, dict):
                all_keys.update(f.keys())
        
        print(f"\n  {name} ({len(group)} events):")
        print(f"    Factor keys found: {sorted(all_keys)}")
        
        # Analyze numeric factors
        numeric_factors = {}
        for key in all_keys:
            values = []
            for f in group:
                if isinstance(f, dict):
                    val = f.get(key)
                    if isinstance(val, (int, float)):
                        values.append(val)
            if values:
                numeric_factors[key] = values
        
        if numeric_factors:
            print(f"    Numeric factors:")
            for key, values in sorted(numeric_factors.items()):
                avg = sum(values) / len(values) if values else 0
                min_val = min(values) if values else 0
                max_val = max(values) if values else 0
                print(f"      {key}: avg={avg:.3f}, min={min_val:.3f}, max={max_val:.3f}, n={len(values)}")
        
        # Show sample factors
        if group:
            print(f"    Sample factors (first event):")
            sample = group[0]
            if isinstance(sample, dict):
                for key, val in sorted(sample.items())[:10]:
                    print(f"      {key}: {val}")
    
    analyze_factors(misses, "MISSES (What we skipped that would have worked)")
    analyze_factors(dodges, "DODGES (What we correctly skipped)")
    analyze_factors(wins, "WINS (What we acted on and succeeded)")
    analyze_factors(failures, "FAILURES (What we acted on and failed)")
    
    # Compare factors between groups
    print(f"\n{'='*80}")
    print("FACTOR COMPARISON")
    print(f"{'='*80}")
    
    def get_avg_factor(group, factor_key):
        values = []
        for f in group:
            if isinstance(f, dict):
                val = f.get(factor_key)
                if isinstance(val, (int, float)):
                    values.append(val)
        return sum(values) / len(values) if values else None
    
    # Find common numeric factors
    all_groups = {
        'misses': misses,
        'dodges': dodges,
        'wins': wins,
        'failures': failures
    }
    
    # Get all factor keys
    all_keys = set()
    for group in all_groups.values():
        for f in group:
            if isinstance(f, dict):
                all_keys.update(f.keys())
    
    # Compare numeric factors
    print(f"\n  Factor Comparison (averages):")
    print(f"    {'Factor':<20} {'Misses':<12} {'Dodges':<12} {'Wins':<12} {'Failures':<12}")
    print(f"    {'-'*20} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    
    for key in sorted(all_keys):
        miss_avg = get_avg_factor(misses, key)
        dodge_avg = get_avg_factor(dodges, key)
        win_avg = get_avg_factor(wins, key)
        fail_avg = get_avg_factor(failures, key)
        
        if any(v is not None for v in [miss_avg, dodge_avg, win_avg, fail_avg]):
            miss_str = f"{miss_avg:.3f}" if miss_avg is not None else "N/A"
            dodge_str = f"{dodge_avg:.3f}" if dodge_avg is not None else "N/A"
            win_str = f"{win_avg:.3f}" if win_avg is not None else "N/A"
            fail_str = f"{fail_avg:.3f}" if fail_avg is not None else "N/A"
            print(f"    {key:<20} {miss_str:<12} {dodge_str:<12} {win_str:<12} {fail_str:<12}")
    
    # Insights
    print(f"\n{'='*80}")
    print("INSIGHTS")
    print(f"{'='*80}")
    print("""
    What we should learn:
    1. If misses have HIGH TS but we skipped → TS threshold too high
    2. If misses have LOW TS but we skipped → Halo/slope blocked us
    3. If failures have LOW TS but we acted → TS threshold too low
    4. If failures have HIGH TS but we acted → Halo/slope too loose
    
    Current system doesn't do this - it just calculates overall pressure.
    We need FACTOR-SPECIFIC tuning, not blanket adjustments.
    """)
    
    # Check if we have the right data
    print(f"\n{'='*80}")
    print("DATA AVAILABILITY CHECK")
    print(f"{'='*80}")
    
    sample_event = s1_events[0] if s1_events else None
    if sample_event:
        factors = sample_event.get('factors', {})
        print(f"  Sample event factors:")
        if isinstance(factors, dict):
            for key, val in sorted(factors.items()):
                print(f"    {key}: {val}")
        else:
            print(f"    Factors is not a dict: {type(factors)}")
        
        # Check for key tuning factors
        key_factors = ['ts_score', 'ts_min', 'halo', 'dist_to_ema', 'slope', 'dx', 'dx_min']
        print(f"\n  Key tuning factors present:")
        for key in key_factors:
            present = any(
                k.lower().replace('_', '') == key.lower().replace('_', '') 
                for k in (factors.keys() if isinstance(factors, dict) else [])
            )
            print(f"    {key}: {'✅' if present else '❌'}")

if __name__ == "__main__":
    main()

