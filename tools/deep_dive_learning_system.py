#!/usr/bin/env python3
"""
Deep Dive into Learning System
Comprehensive exploration of all learning components
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from datetime import datetime, timezone, timedelta
import json

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("LEARNING SYSTEM DEEP DIVE")
    print("=" * 80)
    
    # ========================================================================
    # PART 1: DECISION MAKER LEARNING
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 1: DECISION MAKER LEARNING")
    print("=" * 80)
    
    # 1.1 Learning Configs (Timeframe Weights)
    print("\n📊 1.1 Learning Configs (Timeframe Weights):")
    print("-" * 80)
    try:
        configs = sb.table('learning_configs').select('*').eq('module_id', 'decision_maker').execute()
        if configs.data:
            config = configs.data[0]
            config_data = config.get('config_data', {})
            tf_weights = config_data.get('timeframe_weights', {})
            global_rr = config_data.get('global_rr', {})
            
            print(f"  Module: {config.get('module_id')}")
            print(f"  Last updated: {config.get('updated_at')}")
            print(f"  Updated by: {config.get('updated_by', 'N/A')}")
            
            if tf_weights:
                print("\n  Timeframe Weights:")
                for tf in ['1m', '15m', '1h', '4h']:
                    if tf in tf_weights:
                        data = tf_weights[tf]
                        weight = data.get('weight', 'N/A')
                        rr_short = data.get('rr_short', 'N/A')
                        rr_long = data.get('rr_long', 'N/A')
                        n = data.get('n', 0)
                        updated = data.get('updated_at', 'N/A')
                        print(f"    {tf}:")
                        print(f"      Weight: {weight:.3f}")
                        print(f"      RR Short: {rr_short:.3f} (n={n})")
                        print(f"      RR Long: {rr_long:.3f}")
                        print(f"      Last updated: {updated}")
            
            if global_rr:
                print("\n  Global R/R Baseline:")
                rr_short = global_rr.get('rr_short', 'N/A')
                rr_long = global_rr.get('rr_long', 'N/A')
                n = global_rr.get('n', 0)
                updated = global_rr.get('updated_at', 'N/A')
                print(f"    RR Short: {rr_short:.3f} (n={n})")
                print(f"    RR Long: {rr_long:.3f}")
                print(f"    Last updated: {updated}")
        else:
            print("  ⚠️  No learning_configs found for decision_maker")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 1.2 Position Closed Strands (Input to Learning)
    print("\n📈 1.2 Position Closed Strands (Input to Learning):")
    print("-" * 80)
    try:
        # Get count by timeframe
        strands = sb.table('ad_strands').select('timeframe, created_at').eq('kind', 'position_closed').execute()
        
        by_tf = {}
        for s in strands.data:
            tf = s.get('timeframe', 'unknown')
            if tf not in by_tf:
                by_tf[tf] = []
            by_tf[tf].append(s.get('created_at'))
        
        print(f"  Total position_closed strands: {len(strands.data)}")
        print("\n  By Timeframe:")
        for tf in ['1m', '15m', '1h', '4h']:
            if tf in by_tf:
                count = len(by_tf[tf])
                latest = max(by_tf[tf]) if by_tf[tf] else 'N/A'
                print(f"    {tf}: {count} strands (latest: {latest})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ========================================================================
    # PART 2: PATTERN MINING (PM LEARNING)
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 2: PATTERN MINING (PM LEARNING)")
    print("=" * 80)
    
    # 2.1 Pattern Trade Events
    print("\n📊 2.1 Pattern Trade Events (Fact Table):")
    print("-" * 80)
    try:
        events = sb.table('pattern_trade_events').select('*').order('timestamp', desc=True).limit(100).execute()
        
        if events.data:
            print(f"  Total events: {len(events.data)} (showing last 100)")
            
            # Group by pattern_key and action_category
            by_pattern = {}
            for e in events.data:
                pattern = e.get('pattern_key', 'unknown')
                action = e.get('action_category', 'unknown')
                key = f"{pattern}|{action}"
                if key not in by_pattern:
                    by_pattern[key] = {'count': 0, 'rrs': []}
                by_pattern[key]['count'] += 1
                if e.get('rr') is not None:
                    by_pattern[key]['rrs'].append(e.get('rr'))
            
            print("\n  Top Patterns (by count):")
            sorted_patterns = sorted(by_pattern.items(), key=lambda x: x[1]['count'], reverse=True)
            for pattern, data in sorted_patterns[:10]:
                count = data['count']
                rrs = data['rrs']
                avg_rr = sum(rrs) / len(rrs) if rrs else 0
                print(f"    {pattern}: {count} events, avg RR={avg_rr:.3f}")
        else:
            print("  ⚠️  No pattern_trade_events found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 2.2 Learning Lessons
    print("\n🎓 2.2 Learning Lessons (Mined Patterns):")
    print("-" * 80)
    try:
        lessons = sb.table('learning_lessons').select('*').eq('status', 'active').order('updated_at', desc=True).limit(20).execute()
        
        if lessons.data:
            print(f"  Total active lessons: {len(lessons.data)} (showing last 20)")
            
            # Group by module
            by_module = {}
            for l in lessons.data:
                module = l.get('module', 'unknown')
                if module not in by_module:
                    by_module[module] = []
                by_module[module].append(l)
            
            print("\n  By Module:")
            for module, items in by_module.items():
                print(f"    {module}: {len(items)} lessons")
                
                # Show sample lessons
                for lesson in items[:5]:
                    pattern = lesson.get('pattern_key', 'N/A')
                    n = lesson.get('n', 0)
                    stats = lesson.get('stats', {})
                    if isinstance(stats, dict):
                        avg_rr = stats.get('avg_rr', 'N/A')
                        edge_raw = stats.get('edge_raw', 'N/A')
                        print(f"      {pattern}: n={n}, avg_rr={avg_rr}, edge_raw={edge_raw}")
        else:
            print("  ⚠️  No learning_lessons found")
            print("  💡 This is expected if we don't have enough samples (need N>=33 per pattern)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # ========================================================================
    # PART 3: LEARNING SYSTEM FLOW
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 3: LEARNING SYSTEM FLOW ANALYSIS")
    print("=" * 80)
    
    # 3.1 Check if learning system is processing strands
    print("\n🔄 3.1 Learning System Processing Status:")
    print("-" * 80)
    try:
        # Get recent position_closed strands
        recent_strands = sb.table('ad_strands').select('id, created_at').eq('kind', 'position_closed').order('created_at', desc=True).limit(5).execute()
        
        if recent_strands.data:
            print("  Recent position_closed strands:")
            for s in recent_strands.data:
                print(f"    {s['id']}: {s['created_at']}")
            
            # Check if pattern_trade_events exist for these
            print("\n  Checking if pattern_trade_events were created:")
            for s in recent_strands.data[:3]:
                # Try to find events created around the same time
                strand_time = s['created_at']
                events = sb.table('pattern_trade_events').select('id, timestamp').gte('timestamp', strand_time).limit(5).execute()
                if events.data:
                    print(f"    Strand {s['id'][:20]}...: {len(events.data)} events found")
                else:
                    print(f"    Strand {s['id'][:20]}...: ⚠️  No events found")
        else:
            print("  ⚠️  No recent position_closed strands")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 3.2 Sample Size Analysis
    print("\n📊 3.2 Sample Size Analysis (How close are we to N>=33?):")
    print("-" * 80)
    try:
        events = sb.table('pattern_trade_events').select('pattern_key, action_category, trade_id').execute()
        
        # Group by (pattern_key, action_category) and count unique trades
        by_pattern = {}
        for e in events.data:
            pattern = e.get('pattern_key', 'unknown')
            action = e.get('action_category', 'unknown')
            trade_id = e.get('trade_id')
            key = f"{pattern}|{action}"
            
            if key not in by_pattern:
                by_pattern[key] = set()
            if trade_id:
                by_pattern[key].add(trade_id)
        
        # Sort by count
        sorted_patterns = sorted(by_pattern.items(), key=lambda x: len(x[1]), reverse=True)
        
        print("  Patterns closest to N>=33 threshold:")
        for pattern, trade_ids in sorted_patterns[:15]:
            n = len(trade_ids)
            status = "✅ Ready" if n >= 33 else f"⚠️  Need {33-n} more"
            print(f"    {pattern}: n={n} {status}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("DEEP DIVE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

