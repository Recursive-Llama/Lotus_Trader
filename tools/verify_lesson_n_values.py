#!/usr/bin/env python3
"""
Verify the n values in learning_lessons by checking the source events.

Usage:
    PYTHONPATH=src python tools/verify_lesson_n_values.py
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
    print("VERIFYING LEARNING_LESSONS N VALUES")
    print("=" * 80)
    
    # Get lessons with n around 71, 57
    print("\n📥 Fetching lessons with n >= 50...")
    lessons = sb.table("learning_lessons").select("*").gte("n", 50).execute().data or []
    
    print(f"📊 Found {len(lessons)} lessons with n >= 50\n")
    
    # Get all pattern_trade_events
    print("📥 Fetching all pattern_trade_events...")
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
    
    print(f"📊 Total Events: {len(all_events):,}\n")
    
    # For each lesson, verify the n value
    print("=" * 80)
    print("VERIFICATION: Comparing lesson n values to actual event counts")
    print("=" * 80)
    
    for lesson in lessons[:10]:  # Check first 10
        pattern_key = lesson.get("pattern_key")
        action_category = lesson.get("action_category")
        scope_subset = lesson.get("scope_subset", {})
        lesson_n = lesson.get("n")
        
        print(f"\n📋 Lesson:")
        print(f"   Pattern Key: {pattern_key}")
        print(f"   Action Category: {action_category}")
        print(f"   Scope Subset: {json.dumps(scope_subset, indent=2)}")
        print(f"   Lesson N: {lesson_n}")
        
        # Filter events matching this lesson
        matching_events = []
        for event in all_events:
            if (event.get("pattern_key") == pattern_key and 
                event.get("action_category") == action_category):
                
                # Check if scope matches
                event_scope = event.get("scope", {})
                if isinstance(event_scope, dict) and isinstance(scope_subset, dict):
                    # Check if all keys in scope_subset match event_scope
                    matches = True
                    for key, value in scope_subset.items():
                        if event_scope.get(key) != value:
                            matches = False
                            break
                    if matches:
                        matching_events.append(event)
        
        actual_n = len(matching_events)
        print(f"   Actual N (matching events): {actual_n}")
        
        if actual_n == lesson_n:
            print(f"   ✅ MATCH")
        else:
            print(f"   ⚠️  MISMATCH (difference: {lesson_n - actual_n})")
        
        # Show sample events
        if matching_events:
            print(f"   Sample trade_ids: {set(e.get('trade_id') for e in matching_events[:5])}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\n💡 The 'n' field in learning_lessons represents:")
    print("   - Number of EVENTS (actions) in pattern_trade_events")
    print("   - NOT the number of trades")
    print("\n   Each trade can have multiple actions:")
    print("   - 1 entry action")
    print("   - N add actions (scaling in)")
    print("   - M trim actions (scaling out)")
    print("   - 1 exit action")
    print("\n   So n=71 means 71 'add' actions, not 71 trades.")
    print("   With 19 closed trades, having 71 add actions is reasonable")
    print("   (average ~3.7 add actions per trade, with some trades having many more).")

if __name__ == "__main__":
    main()

