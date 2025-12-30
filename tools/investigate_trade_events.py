#!/usr/bin/env python3
"""
Investigate pattern_trade_events to understand the relationship between
trades and events, and why n=71, n=57 in learning_lessons.

Usage:
    PYTHONPATH=src python tools/investigate_trade_events.py
"""

import os
import sys
from pathlib import Path
from collections import Counter, defaultdict
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("PATTERN_TRADE_EVENTS INVESTIGATION")
    print("=" * 80)
    
    # Get all events
    print("\n📥 Fetching all pattern_trade_events...")
    all_events = []
    page_size = 1000
    offset = 0
    
    while True:
        result = sb.table("pattern_trade_events").select("*").range(offset, offset + page_size - 1).execute()
        if not result.data:
            break
        all_events.extend(result.data)
        offset += page_size
        if len(result.data) < page_size:
            break
    
    print(f"📊 Total Events: {len(all_events):,}")
    
    if not all_events:
        print("❌ No events found")
        return
    
    # Count distinct trades
    trade_ids = set(e.get("trade_id") for e in all_events if e.get("trade_id"))
    print(f"📊 Distinct Trades: {len(trade_ids):,}")
    
    # Events per trade
    events_per_trade = Counter(e.get("trade_id") for e in all_events if e.get("trade_id"))
    if events_per_trade:
        print(f"\n📊 Events per Trade Distribution:")
        print(f"  Min:     {min(events_per_trade.values()):>6}")
        print(f"  Max:     {max(events_per_trade.values()):>6}")
        print(f"  Mean:    {sum(events_per_trade.values())/len(events_per_trade):>6,.1f}")
        print(f"  Median:  {sorted(events_per_trade.values())[len(events_per_trade.values())//2]:>6}")
        
        # Distribution
        buckets = {
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0,
            "5": 0,
            "6": 0,
            "7": 0,
            "8+": 0,
        }
        for count in events_per_trade.values():
            if count == 1:
                buckets["1"] += 1
            elif count == 2:
                buckets["2"] += 1
            elif count == 3:
                buckets["3"] += 1
            elif count == 4:
                buckets["4"] += 1
            elif count == 5:
                buckets["5"] += 1
            elif count == 6:
                buckets["6"] += 1
            elif count == 7:
                buckets["7"] += 1
            else:
                buckets["8+"] += 1
        
        print(f"\n  Distribution:")
        for bucket, count in buckets.items():
            print(f"    {bucket:>3} events: {count:>6,} trades ({count/len(events_per_trade)*100:.1f}%)")
    
    # By action_category
    print(f"\n📊 By Action Category:")
    action_counts = Counter(e.get("action_category") for e in all_events)
    for action, count in action_counts.most_common():
        print(f"  {action or '(null)':<15} {count:>6,} ({count/len(all_events)*100:.1f}%)")
    
    # By pattern_key
    print(f"\n📊 By Pattern Key (Top 10):")
    pattern_counts = Counter(e.get("pattern_key") for e in all_events)
    for pattern, count in pattern_counts.most_common(10):
        print(f"  {pattern or '(null)':<50} {count:>6,}")
    
    # Focus on "add" actions (since all lessons are for "add")
    add_events = [e for e in all_events if e.get("action_category") == "add"]
    print(f"\n📊 ADD Actions Specifically:")
    print(f"  Total Add Events: {len(add_events):,}")
    
    if add_events:
        # Pattern keys for add events
        add_patterns = Counter(e.get("pattern_key") for e in add_events)
        print(f"\n  By Pattern Key (Top 10):")
        for pattern, count in add_patterns.most_common(10):
            print(f"    {pattern or '(null)':<50} {count:>6,}")
        
        # Trades with add events
        trades_with_adds = set(e.get("trade_id") for e in add_events if e.get("trade_id"))
        print(f"\n  Trades with Add Actions: {len(trades_with_adds):,}")
        
        # Adds per trade
        adds_per_trade = Counter(e.get("trade_id") for e in add_events if e.get("trade_id"))
        if adds_per_trade:
            print(f"\n  Add Actions per Trade:")
            print(f"    Min:     {min(adds_per_trade.values()):>6}")
            print(f"    Max:     {max(adds_per_trade.values()):>6}")
            print(f"    Mean:    {sum(adds_per_trade.values())/len(adds_per_trade):>6,.1f}")
            print(f"    Median:  {sorted(adds_per_trade.values())[len(adds_per_trade.values())//2]:>6}")
            
            # Distribution
            add_buckets = {
                "1": 0,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6+": 0,
            }
            for count in adds_per_trade.values():
                if count == 1:
                    add_buckets["1"] += 1
                elif count == 2:
                    add_buckets["2"] += 1
                elif count == 3:
                    add_buckets["3"] += 1
                elif count == 4:
                    add_buckets["4"] += 1
                elif count == 5:
                    add_buckets["5"] += 1
                else:
                    add_buckets["6+"] += 1
            
            print(f"\n    Distribution:")
            for bucket, count in add_buckets.items():
                print(f"      {bucket:>3} adds: {count:>6,} trades ({count/len(adds_per_trade)*100:.1f}%)")
    
    # Sample events to understand structure
    print(f"\n📊 Sample Events (showing structure):")
    for i, event in enumerate(all_events[:5]):
        print(f"\n  Event {i+1}:")
        print(f"    trade_id: {event.get('trade_id')}")
        print(f"    pattern_key: {event.get('pattern_key')}")
        print(f"    action_category: {event.get('action_category')}")
        print(f"    rr: {event.get('rr')}")
        print(f"    timestamp: {event.get('timestamp')}")
    
    # Check how lesson_builder groups events
    print(f"\n📊 How Lesson Builder Groups Events:")
    print(f"  Lesson builder groups by (pattern_key, action_category, scope_subset)")
    print(f"  For 'add' actions with pattern_key='uptrend.S3.add':")
    
    s3_add_events = [e for e in all_events 
                     if e.get("action_category") == "add" 
                     and "S3" in str(e.get("pattern_key", ""))]
    
    if s3_add_events:
        print(f"    Found {len(s3_add_events):,} S3 add events")
        
        # Group by scope to see how many events per scope slice
        scope_groups = defaultdict(list)
        for event in s3_add_events:
            scope = event.get("scope", {})
            # Create a simplified scope key for grouping
            scope_key = tuple(sorted(scope.items())) if isinstance(scope, dict) else str(scope)
            scope_groups[scope_key].append(event)
        
        print(f"    Found {len(scope_groups):,} distinct scope combinations")
        
        # Count events per scope group
        events_per_scope = [len(events) for events in scope_groups.values()]
        if events_per_scope:
            print(f"    Events per scope slice:")
            print(f"      Min:     {min(events_per_scope):>6}")
            print(f"      Max:     {max(events_per_scope):>6}")
            print(f"      Mean:    {sum(events_per_scope)/len(events_per_scope):>6,.1f}")
            print(f"      Median:  {sorted(events_per_scope)[len(events_per_scope)//2]:>6}")
    
    print("\n" + "=" * 80)
    print("INVESTIGATION COMPLETE")
    print("=" * 80)
    
    print("\n💡 KEY INSIGHT:")
    print("   The 'n' field in learning_lessons represents the NUMBER OF EVENTS (actions),")
    print("   not the number of trades. Each trade can have multiple actions:")
    print("   - Entry action")
    print("   - Multiple Add actions (scaling in)")
    print("   - Trim actions (scaling out)")
    print("   - Exit action")
    print("\n   So if you have 10 closed trades, but each trade has 5-7 actions,")
    print("   you'll have 50-70 events, which explains n=71, n=57 in learning_lessons.")

if __name__ == "__main__":
    main()

