#!/usr/bin/env python3
"""
Trace the flow of how pm_strength lessons are created from closed trades.

Usage:
    PYTHONPATH=src python tools/trace_pm_strength_flow.py
"""

import os
import sys
from pathlib import Path
from collections import Counter, defaultdict
from dotenv import load_dotenv
from supabase import create_client
import json

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
    print("TRACING PM_STRENGTH FLOW: FROM CLOSED TRADES TO LESSONS")
    print("=" * 80)
    
    # Step 1: Check position_closed strands
    print("\n1️⃣  POSITION_CLOSED STRANDS (Source)")
    print("-" * 80)
    closed_strands = sb.table("ad_strands").select("*").eq("kind", "position_closed").eq("module", "pm").limit(20).execute().data or []
    print(f"   Found {len(closed_strands)} position_closed strands")
    
    if closed_strands:
        trade_ids = [s.get("content", {}).get("trade_id") for s in closed_strands if s.get("content", {}).get("trade_id")]
        print(f"   Distinct trade_ids: {len(set(trade_ids))}")
        
        # Sample strand
        sample = closed_strands[0]
        print(f"\n   Sample strand:")
        print(f"     trade_id: {sample.get('content', {}).get('trade_id')}")
        print(f"     trade_summary: {sample.get('content', {}).get('trade_summary', {})}")
    
    # Step 2: Check pattern_trade_events
    print("\n2️⃣  PATTERN_TRADE_EVENTS (After Aggregator)")
    print("-" * 80)
    events = sb.table("pattern_trade_events").select("*").limit(100).execute().data or []
    print(f"   Found {len(events)} events in pattern_trade_events")
    
    if events:
        # Count distinct trades
        trade_ids = [e.get("trade_id") for e in events if e.get("trade_id")]
        distinct_trades = len(set(trade_ids))
        print(f"   Distinct trade_ids: {distinct_trades}")
        print(f"   Events per trade: {len(events) / distinct_trades:.1f} (average)")
        
        # Show distribution
        events_per_trade = Counter(trade_ids)
        print(f"\n   Events per trade distribution:")
        for count, num_trades in Counter(events_per_trade.values()).most_common(10):
            print(f"     {count} events: {num_trades} trades")
        
        # Check if same trade_id has same rr
        print(f"\n   Checking: Do all events from same trade have same RR?")
        trade_rrs = defaultdict(set)
        for event in events:
            trade_id = event.get("trade_id")
            rr = event.get("rr")
            if trade_id and rr is not None:
                trade_rrs[trade_id].add(rr)
        
        same_rr_count = sum(1 for rrs in trade_rrs.values() if len(rrs) == 1)
        different_rr_count = sum(1 for rrs in trade_rrs.values() if len(rrs) > 1)
        print(f"     Trades with same RR for all actions: {same_rr_count}")
        print(f"     Trades with different RR for actions: {different_rr_count}")
        
        # Sample events from same trade
        print(f"\n   Sample: Events from same trade_id:")
        sample_trade_id = trade_ids[0] if trade_ids else None
        if sample_trade_id:
            same_trade_events = [e for e in events if e.get("trade_id") == sample_trade_id]
            print(f"     trade_id: {sample_trade_id}")
            print(f"     Number of events: {len(same_trade_events)}")
            for i, event in enumerate(same_trade_events[:5]):
                print(f"       Event {i+1}: pattern_key={event.get('pattern_key')}, action_category={event.get('action_category')}, rr={event.get('rr')}")
    
    # Step 3: Check learning_lessons
    print("\n3️⃣  LEARNING_LESSONS (After Lesson Builder)")
    print("-" * 80)
    lessons = sb.table("learning_lessons").select("*").eq("lesson_type", "pm_strength").limit(10).execute().data or []
    print(f"   Found {len(lessons)} pm_strength lessons (showing first 10)")
    
    if lessons:
        # Sample lesson
        sample_lesson = lessons[0]
        print(f"\n   Sample lesson:")
        print(f"     pattern_key: {sample_lesson.get('pattern_key')}")
        print(f"     action_category: {sample_lesson.get('action_category')}")
        print(f"     n: {sample_lesson.get('n')}")
        print(f"     scope_subset: {json.dumps(sample_lesson.get('scope_subset', {}), indent=2)}")
        
        # Verify: Count matching events
        pattern_key = sample_lesson.get("pattern_key")
        action_category = sample_lesson.get("action_category")
        scope_subset = sample_lesson.get("scope_subset", {})
        
        print(f"\n   Verifying: Counting matching events in pattern_trade_events...")
        all_events = sb.table("pattern_trade_events").select("*").execute().data or []
        matching_events = []
        for event in all_events:
            if (event.get("pattern_key") == pattern_key and 
                event.get("action_category") == action_category):
                event_scope = event.get("scope", {})
                if isinstance(event_scope, dict) and isinstance(scope_subset, dict):
                    matches = True
                    for key, value in scope_subset.items():
                        if event_scope.get(key) != value:
                            matches = False
                            break
                    if matches:
                        matching_events.append(event)
        
        print(f"     Lesson n: {sample_lesson.get('n')}")
        print(f"     Matching events: {len(matching_events)}")
        print(f"     Matching distinct trades: {len(set(e.get('trade_id') for e in matching_events))}")
        
        if len(matching_events) == sample_lesson.get('n'):
            print(f"     ✅ MATCH: n equals number of events")
        else:
            print(f"     ⚠️  MISMATCH")
    
    print("\n" + "=" * 80)
    print("KEY FINDING")
    print("=" * 80)
    print("""
The flow is:
1. Closed Trade → position_closed strand (1 per trade)
2. Aggregator → pattern_trade_events (1 row per ACTION, not per trade)
   - Each action from the same trade gets the SAME RR (final trade R/R)
   - So if a trade has 5 actions, it creates 5 rows with same trade_id and same rr
3. Lesson Builder → learning_lessons (counts EVENTS, not trades)
   - n = number of events (actions) matching the pattern+scope
   - NOT the number of distinct trades

QUESTION: Is this the intended design?
- If YES: n represents actions, which is correct
- If NO: Should n represent distinct trades instead?
    """)

if __name__ == "__main__":
    main()

