#!/usr/bin/env python3
"""
Check why no lessons exist despite having n=52 for S2.trim
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
import json

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("INVESTIGATING: Why No Lessons Despite n=52")
    print("=" * 80)
    
    # Check pattern_trade_events
    events = sb.table('pattern_trade_events').select('*').execute()
    
    if events.data:
        print(f"\n  Pattern Trade Events: {len(events.data)}")
        
        # Check S2.trim specifically
        s2_trim = [e for e in events.data if 'S2' in e.get('pattern_key', '') and e.get('action_category') == 'trim']
        print(f"\n  S2.trim events: {len(s2_trim)}")
        
        if s2_trim:
            print(f"\n  Sample S2.trim event:")
            sample = s2_trim[0]
            print(f"    pattern_key: {sample.get('pattern_key')}")
            print(f"    action_category: {sample.get('action_category')}")
            print(f"    scope: {sample.get('scope')}")
            print(f"    rr: {sample.get('rr')}")
            print(f"    trade_id: {sample.get('trade_id')}")
            
            # Check unique trade_ids
            trade_ids = set(e.get('trade_id') for e in s2_trim if e.get('trade_id'))
            print(f"\n  Unique trade_ids: {len(trade_ids)}")
            
            # Check if pattern_key has "module=pm|pattern_key=" format
            pattern_key = sample.get('pattern_key', '')
            if 'pattern_key=' in pattern_key:
                print(f"\n  ⚠️  Pattern key has 'pattern_key=' prefix: {pattern_key}")
                print(f"  This might cause issues with Lesson Builder matching")
            else:
                print(f"\n  ✅ Pattern key format looks clean: {pattern_key}")
    
    # Check what Lesson Builder expects
    print("\n" + "=" * 80)
    print("LESSON BUILDER EXPECTATIONS")
    print("=" * 80)
    
    print("""
    Lesson Builder (lesson_builder_v5.py):
    - Groups by (pattern_key, action_category)
    - Expects pattern_key to match exactly
    - Mines recursively with N_MIN_SLICE = 33
    - Deduplicates by trade_id
    
    If pattern_key format doesn't match, lessons won't be created.
    """)
    
    # Check if Lesson Builder has run
    print("\n" + "=" * 80)
    print("CHECKING IF LESSON BUILDER HAS RUN")
    print("=" * 80)
    
    # Check for any lessons (any type)
    all_lessons = sb.table('learning_lessons').select('*').limit(10).execute()
    print(f"\n  Total lessons (any type): {len(all_lessons.data) if all_lessons.data else 0}")
    
    if all_lessons.data:
        print(f"\n  Sample lesson:")
        sample = all_lessons.data[0]
        print(f"    module: {sample.get('module')}")
        print(f"    lesson_type: {sample.get('lesson_type')}")
        print(f"    pattern_key: {sample.get('pattern_key')}")
        print(f"    n: {sample.get('n')}")
    else:
        print("\n  ⚠️  No lessons exist at all - Lesson Builder may not have run")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

