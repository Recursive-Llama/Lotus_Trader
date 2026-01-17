#!/usr/bin/env python3
"""
Explore Learning System Data
Shows what the learning system has learned from closed trades
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from datetime import datetime, timezone, timedelta
import json

def main():
    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("LEARNING SYSTEM DATA EXPLORATION")
    print("=" * 80)
    
    # 1. Check position_closed strands
    print("\n📊 1. Position Closed Strands (Input to Learning System):")
    print("-" * 80)
    try:
        strands = sb.table('ad_strands').select('id, kind, created_at').eq('kind', 'position_closed').order('created_at', desc=True).limit(10).execute()
        if strands.data:
            print(f"  Found {len(strands.data)} recent position_closed strands")
            print(f"  Most recent: {strands.data[0]['created_at']}")
            
            # Get total count
            total = sb.table('ad_strands').select('id', count='exact').eq('kind', 'position_closed').execute()
            print(f"  Total position_closed strands: {total.count if hasattr(total, 'count') else 'N/A'}")
        else:
            print("  ⚠️  No position_closed strands found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 2. Check pattern_trade_events (fact table)
    print("\n📈 2. Pattern Trade Events (Fact Table):")
    print("-" * 80)
    try:
        events = sb.table('pattern_trade_events').select('id, pattern_key, action_category, rr, pnl_usd, timestamp').order('timestamp', desc=True).limit(10).execute()
        if events.data:
            print(f"  Found {len(events.data)} recent events")
            print(f"  Most recent: {events.data[0]['timestamp']}")
            
            # Get total count
            total = sb.table('pattern_trade_events').select('id', count='exact').execute()
            print(f"  Total events: {total.count if hasattr(total, 'count') else 'N/A'}")
            
            # Show sample events
            print("\n  Sample events:")
            for event in events.data[:5]:
                print(f"    {event['pattern_key']} | {event['action_category']} | RR: {event.get('rr', 'N/A'):.2f} | PnL: ${event.get('pnl_usd', 0):.2f}")
        else:
            print("  ⚠️  No pattern_trade_events found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 3. Check learning_lessons (mined patterns)
    print("\n🎓 3. Learning Lessons (Mined Patterns):")
    print("-" * 80)
    try:
        lessons = sb.table('learning_lessons').select('*').eq('status', 'active').order('updated_at', desc=True).limit(10).execute()
        if lessons.data:
            print(f"  Found {len(lessons.data)} active lessons")
            
            # Get total count
            total = sb.table('learning_lessons').select('id', count='exact').eq('status', 'active').execute()
            print(f"  Total active lessons: {total.count if hasattr(total, 'count') else 'N/A'}")
            
            # Show sample lessons
            print("\n  Sample lessons:")
            for lesson in lessons.data[:5]:
                pattern = lesson.get('pattern_key', 'N/A')
                n = lesson.get('n', 0)
                stats = lesson.get('stats', {})
                avg_rr = stats.get('avg_rr', 'N/A') if isinstance(stats, dict) else 'N/A'
                print(f"    {pattern} | n={n} | avg_rr={avg_rr}")
        else:
            print("  ⚠️  No learning_lessons found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 4. Check learning_configs (timeframe weights)
    print("\n⚙️  4. Learning Configs (Timeframe Weights):")
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
            
            if tf_weights:
                print("\n  Timeframe Weights:")
                for tf, data in tf_weights.items():
                    if isinstance(data, dict):
                        weight = data.get('weight', 'N/A')
                        rr_short = data.get('rr_short', 'N/A')
                        n = data.get('n', 0)
                        print(f"    {tf}: weight={weight:.3f} | rr_short={rr_short:.3f} | n={n}")
            
            if global_rr:
                print("\n  Global R/R Baseline:")
                rr_short = global_rr.get('rr_short', 'N/A')
                rr_long = global_rr.get('rr_long', 'N/A')
                n = global_rr.get('n', 0)
                print(f"    rr_short={rr_short:.3f} | rr_long={rr_long:.3f} | n={n}")
        else:
            print("  ⚠️  No learning_configs found for decision_maker")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 5. Check learning_coefficients
    print("\n🔢 5. Learning Coefficients:")
    print("-" * 80)
    try:
        coeffs = sb.table('learning_coefficients').select('*').order('updated_at', desc=True).limit(20).execute()
        if coeffs.data:
            print(f"  Found {len(coeffs.data)} recent coefficients")
            
            # Group by module and scope
            by_module = {}
            for c in coeffs.data:
                module = c.get('module', 'unknown')
                scope = c.get('scope', 'unknown')
                key = f"{module}.{scope}"
                if key not in by_module:
                    by_module[key] = []
                by_module[key].append(c)
            
            print("\n  By Module/Scope:")
            for key, items in by_module.items():
                print(f"    {key}: {len(items)} coefficients")
                for item in items[:3]:  # Show first 3
                    name = item.get('name', 'N/A')
                    weight = item.get('weight', 'N/A')
                    n = item.get('n', 0)
                    print(f"      {name}: weight={weight:.3f} | n={n}")
        else:
            print("  ⚠️  No learning_coefficients found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 6. Check pm_overrides (actionable rules)
    print("\n🎯 6. PM Overrides (Actionable Rules):")
    print("-" * 80)
    try:
        overrides = sb.table('pm_overrides').select('*').eq('status', 'active').order('updated_at', desc=True).limit(10).execute()
        if overrides.data:
            print(f"  Found {len(overrides.data)} active overrides")
            
            # Get total count
            total = sb.table('pm_overrides').select('id', count='exact').eq('status', 'active').execute()
            print(f"  Total active overrides: {total.count if hasattr(total, 'count') else 'N/A'}")
            
            # Show sample overrides
            print("\n  Sample overrides:")
            for override in overrides.data[:5]:
                pattern = override.get('pattern_key', 'N/A')
                multiplier = override.get('size_multiplier', 'N/A')
                print(f"    {pattern} | multiplier={multiplier}")
        else:
            print("  ⚠️  No pm_overrides found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

