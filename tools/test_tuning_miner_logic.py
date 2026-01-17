#!/usr/bin/env python3
"""
Test TuningMiner Logic - Simulate what would happen
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
import pandas as pd

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("TESTING TUNING MINER LOGIC")
    print("=" * 80)
    
    # Simulate what TuningMiner does
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    
    # Fetch events (what TuningMiner sees)
    res = sb.table("pattern_episode_events")\
        .select("*")\
        .neq("outcome", "null")\
        .gte("timestamp", cutoff)\
        .execute()
    
    events = res.data or []
    print(f"\n📊 Events with outcomes (last 90 days): {len(events)}")
    
    if not events:
        print("  ⚠️  No events to process")
        return
    
    # Convert to DataFrame (like TuningMiner does)
    df = pd.DataFrame(events)
    
    # Flatten scope
    scope_keys = set()
    for scope in df['scope']:
        if isinstance(scope, dict):
            scope_keys.update(scope.keys())
    
    sorted_dims = sorted(list(scope_keys))
    print(f"\n  Scope dimensions: {sorted_dims}")
    
    for key in sorted_dims:
        df[f"scope_{key}"] = df['scope'].apply(lambda x: x.get(key) if isinstance(x, dict) else None)
    
    # Group by pattern_key first
    print(f"\n📊 By Pattern Key:")
    grouped = df.groupby('pattern_key')
    for pattern_key, group in grouped:
        print(f"\n  {pattern_key}: {len(group)} events")
        
        # Check acted vs skipped
        acted = group[group['decision'] == 'acted']
        skipped = group[group['decision'] == 'skipped']
        
        print(f"    Acted: {len(acted)}, Skipped: {len(skipped)}")
        
        if len(acted) > 0:
            success_acted = len(acted[acted['outcome'] == 'success'])
            failure_acted = len(acted[acted['outcome'] == 'failure'])
            print(f"      Success: {success_acted}, Failure: {failure_acted}")
        
        if len(skipped) > 0:
            success_skipped = len(skipped[skipped['outcome'] == 'success'])
            failure_skipped = len(skipped[skipped['outcome'] == 'failure'])
            print(f"      Success: {success_skipped}, Failure: {failure_skipped}")
        
        # Check if would pass N_MIN=33
        if len(group) >= 33:
            print(f"    ✅ Would create lesson for global slice (n={len(group)})")
            
            # Check scope slices
            print(f"    Checking scope slices...")
            for dim in sorted_dims[:5]:  # Check first 5 dimensions
                col = f"scope_{dim}"
                if col in df.columns:
                    counts = group[col].value_counts()
                    valid = counts[counts >= 33]
                    if len(valid) > 0:
                        print(f"      {dim}: {len(valid)} slices with n>=33")
                        for val, count in valid.items():
                            print(f"        {val}: {count} events")
                    else:
                        print(f"      {dim}: No slices with n>=33 (max: {counts.max() if len(counts) > 0 else 0})")
        else:
            print(f"    ⚠️  Would NOT create lesson (n={len(group)} < 33)")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\n  If TuningMiner ran, it should create lessons for:")
    print("    1. Global slice (all events for a pattern)")
    print("    2. Scope slices that have n>=33")
    print("\n  Check if TuningMiner is actually running, or if there's a bug in the mining logic.")

if __name__ == "__main__":
    main()

