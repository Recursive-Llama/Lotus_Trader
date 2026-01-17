#!/usr/bin/env python3
"""
Analyze PM Tuning System Flow - What's Working, What's Not
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

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("PM TUNING SYSTEM FLOW ANALYSIS")
    print("=" * 80)
    
    # ========================================================================
    # STEP 1: Pattern Episode Events (Raw Data)
    # ========================================================================
    print("\n📊 STEP 1: Pattern Episode Events (Raw Data)")
    print("-" * 80)
    
    try:
        # Get ALL events
        all_events = sb.table('pattern_episode_events').select('*').execute()
        
        if not all_events.data:
            print("  ❌ No episode events found")
            return
        
        total = len(all_events.data)
        print(f"  Total events: {total}")
        
        # Group by pattern_key
        by_pattern = {}
        for e in all_events.data:
            pattern = e.get('pattern_key', 'unknown')
            outcome = e.get('outcome')
            decision = e.get('decision', 'unknown')
            
            if pattern not in by_pattern:
                by_pattern[pattern] = {
                    'total': 0,
                    'with_outcome': 0,
                    'pending': 0,
                    'acted': 0,
                    'skipped': 0,
                    'success': 0,
                    'failure': 0
                }
            
            by_pattern[pattern]['total'] += 1
            if outcome is not None:
                by_pattern[pattern]['with_outcome'] += 1
                if outcome == 'success':
                    by_pattern[pattern]['success'] += 1
                elif outcome == 'failure':
                    by_pattern[pattern]['failure'] += 1
            else:
                by_pattern[pattern]['pending'] += 1
            
            if decision == 'acted':
                by_pattern[pattern]['acted'] += 1
            elif decision == 'skipped':
                by_pattern[pattern]['skipped'] += 1
        
        print("\n  By Pattern:")
        for pattern, data in sorted(by_pattern.items(), key=lambda x: x[1]['total'], reverse=True):
            print(f"    {pattern}:")
            print(f"      Total: {data['total']}, With Outcome: {data['with_outcome']}, Pending: {data['pending']}")
            print(f"      Acted: {data['acted']}, Skipped: {data['skipped']}")
            print(f"      Success: {data['success']}, Failure: {data['failure']}")
            
            # Check if would pass N_MIN=33 filter (needs outcome)
            if data['with_outcome'] >= 33:
                print(f"      ✅ Would pass N_MIN=33 filter")
            else:
                print(f"      ⚠️  Would NOT pass N_MIN=33 filter (need {33 - data['with_outcome']} more with outcomes)")
        
        # Check what tuning_miner would see
        print("\n  What TuningMiner Sees (events with outcomes, last 90 days):")
        cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
        events_with_outcomes = [e for e in all_events.data 
                               if e.get('outcome') is not None 
                               and e.get('timestamp', '') >= cutoff]
        
        print(f"    Events with outcomes (last 90 days): {len(events_with_outcomes)}")
        
        # Group by pattern
        miner_by_pattern = {}
        for e in events_with_outcomes:
            pattern = e.get('pattern_key', 'unknown')
            if pattern not in miner_by_pattern:
                miner_by_pattern[pattern] = 0
            miner_by_pattern[pattern] += 1
        
        for pattern, count in sorted(miner_by_pattern.items(), key=lambda x: x[1], reverse=True):
            status = "✅ Ready" if count >= 33 else f"⚠️  Need {33 - count} more"
            print(f"      {pattern}: {count} {status}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # STEP 2: Scope Analysis (What happens after scope slicing?)
    # ========================================================================
    print("\n📊 STEP 2: Scope Slicing Impact")
    print("-" * 80)
    
    try:
        # Get events with outcomes
        events_with_outcomes = [e for e in all_events.data if e.get('outcome') is not None]
        
        if not events_with_outcomes:
            print("  ⚠️  No events with outcomes to analyze")
        else:
            # Analyze scope dimensions
            scope_dims = set()
            for e in events_with_outcomes:
                scope = e.get('scope', {})
                if isinstance(scope, dict):
                    scope_dims.update(scope.keys())
            
            print(f"  Scope dimensions found: {sorted(scope_dims)}")
            
            # For main pattern, show scope distribution
            main_pattern = sorted(by_pattern.items(), key=lambda x: x[1]['with_outcome'], reverse=True)[0][0]
            main_events = [e for e in events_with_outcomes if e.get('pattern_key') == main_pattern]
            
            print(f"\n  Main pattern: {main_pattern} ({len(main_events)} events with outcomes)")
            
            # Show scope value distributions
            for dim in sorted(scope_dims):
                values = {}
                for e in main_events:
                    scope = e.get('scope', {})
                    if isinstance(scope, dict):
                        val = scope.get(dim)
                        if val:
                            values[val] = values.get(val, 0) + 1
                
                if values:
                    print(f"\n    {dim}:")
                    for val, count in sorted(values.items(), key=lambda x: x[1], reverse=True):
                        status = "✅" if count >= 33 else "⚠️"
                        print(f"      {val}: {count} {status}")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # STEP 3: Learning Lessons (What would be mined?)
    # ========================================================================
    print("\n📊 STEP 3: Learning Lessons (What Would Be Mined?)")
    print("-" * 80)
    
    try:
        lessons = sb.table('learning_lessons').select('*').execute()
        
        if lessons.data:
            print(f"  Found {len(lessons.data)} lessons")
            
            # Group by lesson_type
            by_type = {}
            for l in lessons.data:
                lesson_type = l.get('lesson_type', 'unknown')
                if lesson_type not in by_type:
                    by_type[lesson_type] = []
                by_type[lesson_type].append(l)
            
            for lesson_type, items in by_type.items():
                print(f"\n  {lesson_type}: {len(items)} lessons")
                for lesson in items[:5]:
                    pattern = lesson.get('pattern_key', 'N/A')
                    n = lesson.get('n', 0)
                    print(f"    {pattern}: n={n}")
        else:
            print("  ⚠️  No lessons found (expected if N_MIN=33 not met)")
            print("  💡 This is the bottleneck - need enough events with outcomes")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ========================================================================
    # STEP 4: PM Overrides (Final Output)
    # ========================================================================
    print("\n📊 STEP 4: PM Overrides (Final Output)")
    print("-" * 80)
    
    try:
        overrides = sb.table('pm_overrides').select('*').execute()
        
        if overrides.data:
            print(f"  Found {len(overrides.data)} overrides")
        else:
            print("  ⚠️  No overrides found")
            print("  💡 This is expected - no lessons = no overrides")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ========================================================================
    # SUMMARY: System Flow Status
    # ========================================================================
    print("\n" + "=" * 80)
    print("SYSTEM FLOW STATUS")
    print("=" * 80)
    
    print("\n  Flow: Episode Events → TuningMiner → Learning Lessons → Override Materializer → PM Overrides")
    print("\n  Current Status:")
    
    # Count events with outcomes
    events_with_outcomes = [e for e in all_events.data if e.get('outcome') is not None]
    print(f"    ✅ Episode Events: {len(events_with_outcomes)} with outcomes (ready for mining)")
    
    # Check if any pattern has enough
    main_pattern_data = sorted(by_pattern.items(), key=lambda x: x[1]['with_outcome'], reverse=True)[0][1]
    if main_pattern_data['with_outcome'] >= 33:
        print(f"    ✅ TuningMiner: Would find patterns (main pattern has {main_pattern_data['with_outcome']} events)")
    else:
        print(f"    ⚠️  TuningMiner: Main pattern needs {33 - main_pattern_data['with_outcome']} more events with outcomes")
    
    lessons_count = len(lessons.data) if 'lessons' in locals() and lessons.data else 0
    if lessons_count > 0:
        print(f"    ✅ Learning Lessons: {lessons_count} lessons found")
    else:
        print(f"    ⚠️  Learning Lessons: 0 lessons (N_MIN=33 not met)")
    
    overrides_count = len(overrides.data) if 'overrides' in locals() and overrides.data else 0
    if overrides_count > 0:
        print(f"    ✅ PM Overrides: {overrides_count} overrides")
    else:
        print(f"    ⚠️  PM Overrides: 0 overrides (no lessons to materialize)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

