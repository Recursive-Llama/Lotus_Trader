#!/usr/bin/env python3
"""
Investigate PM Tuning System - Current Database State
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
    print("PM TUNING SYSTEM - DATABASE INVESTIGATION")
    print("=" * 80)
    
    # ========================================================================
    # 1. PATTERN TRADE EVENTS (Fact Table)
    # ========================================================================
    print("\n📊 1. Pattern Trade Events (Fact Table):")
    print("-" * 80)
    try:
        # Get recent events
        events = sb.table('pattern_trade_events').select('*').order('timestamp', desc=True).limit(100).execute()
        
        # Count total by getting all (limited query)
        all_events = sb.table('pattern_trade_events').select('id').limit(10000).execute()
        total_count = len(all_events.data) if all_events.data else 0
        
        print(f"  Total events (sampled): {total_count}+")
        
        if events.data:
            print(f"  Recent events (last 20):")
            
            # Group by pattern_key and action_category
            by_pattern = {}
            for e in events.data:
                pattern = e.get('pattern_key', 'unknown')
                action = e.get('action_category', 'unknown')
                key = f"{pattern}|{action}"
                if key not in by_pattern:
                    by_pattern[key] = {'count': 0, 'rrs': [], 'pnls': []}
                by_pattern[key]['count'] += 1
                if e.get('rr') is not None:
                    by_pattern[key]['rrs'].append(e.get('rr'))
                if e.get('pnl_usd') is not None:
                    by_pattern[key]['pnls'].append(e.get('pnl_usd'))
            
            print("\n  Top Patterns (by count in recent 20):")
            sorted_patterns = sorted(by_pattern.items(), key=lambda x: x[1]['count'], reverse=True)
            for pattern, data in sorted_patterns[:10]:
                count = data['count']
                rrs = data['rrs']
                pnls = data['pnls']
                avg_rr = sum(rrs) / len(rrs) if rrs else 0
                avg_pnl = sum(pnls) / len(pnls) if pnls else 0
                print(f"    {pattern}: {count} events, avg RR={avg_rr:.3f}, avg PnL=${avg_pnl:.2f}")
        else:
            print("  ⚠️  No pattern_trade_events found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 2. PATTERN TRADE EVENTS BY PATTERN (Full Count)
    # ========================================================================
    print("\n📈 2. Pattern Trade Events - Full Analysis (All Time):")
    print("-" * 80)
    try:
        # Get all events grouped by pattern_key and action_category
        all_events = sb.table('pattern_trade_events').select('pattern_key, action_category, rr, pnl_usd, trade_id').execute()
        
        # Group by (pattern_key, action_category)
        by_pattern = {}
        for e in all_events.data:
            pattern = e.get('pattern_key', 'unknown')
            action = e.get('action_category', 'unknown')
            key = f"{pattern}|{action}"
            
            if key not in by_pattern:
                by_pattern[key] = {'count': 0, 'rrs': [], 'pnls': [], 'trade_ids': set()}
            
            by_pattern[key]['count'] += 1
            if e.get('rr') is not None:
                by_pattern[key]['rrs'].append(e.get('rr'))
            if e.get('pnl_usd') is not None:
                by_pattern[key]['pnls'].append(e.get('pnl_usd'))
            if e.get('trade_id'):
                by_pattern[key]['trade_ids'].add(e.get('trade_id'))
        
        # Calculate stats
        pattern_stats = []
        for key, data in by_pattern.items():
            parts = key.split('|')
            pattern = parts[0] if len(parts) > 0 else 'unknown'
            action = parts[1] if len(parts) > 1 else 'unknown'
            n = data['count']
            unique_trades = len(data['trade_ids'])
            rrs = data['rrs']
            pnls = data['pnls']
            
            avg_rr = sum(rrs) / len(rrs) if rrs else 0
            avg_pnl = sum(pnls) / len(pnls) if pnls else 0
            total_pnl = sum(pnls) if pnls else 0
            
            # Check if close to N_MIN (33)
            n_min = 33
            status = "✅ Ready" if n >= n_min else f"⚠️  Need {n_min - n} more"
            
            pattern_stats.append({
                'pattern': pattern,
                'action': action,
                'n': n,
                'unique_trades': unique_trades,
                'avg_rr': avg_rr,
                'avg_pnl': avg_pnl,
                'total_pnl': total_pnl,
                'status': status
            })
        
        # Sort by n (descending)
        pattern_stats.sort(key=lambda x: x['n'], reverse=True)
        
        print(f"  Total unique patterns: {len(pattern_stats)}")
        print(f"  N_MIN threshold: 33")
        print(f"\n  Patterns closest to N>=33:")
        for stat in pattern_stats[:20]:
            print(f"    {stat['pattern']} | {stat['action']}: n={stat['n']} (trades={stat['unique_trades']}) {stat['status']}")
            print(f"      Avg RR: {stat['avg_rr']:.3f}, Avg PnL: ${stat['avg_pnl']:.2f}, Total PnL: ${stat['total_pnl']:.2f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 3. LEARNING LESSONS (Mined Patterns)
    # ========================================================================
    print("\n🎓 3. Learning Lessons (Mined Patterns):")
    print("-" * 80)
    try:
        lessons = sb.table('learning_lessons').select('*').order('updated_at', desc=True).limit(50).execute()
        
        if lessons.data:
            print(f"  Total lessons: {len(lessons.data)} (showing last 50)")
            
            # Group by module and lesson_type
            by_module = {}
            by_type = {}
            for l in lessons.data:
                module = l.get('module', 'unknown')
                lesson_type = l.get('lesson_type', 'unknown')
                
                if module not in by_module:
                    by_module[module] = []
                by_module[module].append(l)
                
                if lesson_type not in by_type:
                    by_type[lesson_type] = []
                by_type[lesson_type].append(l)
            
            print("\n  By Module:")
            for module, items in by_module.items():
                print(f"    {module}: {len(items)} lessons")
            
            print("\n  By Lesson Type:")
            for lesson_type, items in by_type.items():
                print(f"    {lesson_type}: {len(items)} lessons")
            
            print("\n  Sample Lessons:")
            for l in lessons.data[:10]:
                pattern = l.get('pattern_key', 'N/A')
                n = l.get('n', 0)
                stats = l.get('stats', {})
                if isinstance(stats, dict):
                    avg_rr = stats.get('avg_rr', 'N/A')
                    edge_raw = stats.get('edge_raw', 'N/A')
                    decay_meta = stats.get('decay_meta', {})
                    decay_state = decay_meta.get('state', 'N/A') if isinstance(decay_meta, dict) else 'N/A'
                    print(f"    {pattern}: n={n}, avg_rr={avg_rr}, edge_raw={edge_raw}, decay={decay_state}")
        else:
            print("  ⚠️  No learning_lessons found")
            print("  💡 This is expected if we don't have enough samples (need N>=33 per pattern)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 4. PM OVERRIDES (Actionable Rules)
    # ========================================================================
    print("\n🎯 4. PM Overrides (Actionable Rules):")
    print("-" * 80)
    try:
        # Try to get overrides - check schema first
        overrides = sb.table('pm_overrides').select('*').limit(50).execute()
        
        if overrides.data:
            print(f"  Total overrides: {len(overrides.data)} (showing first 50)")
            
            # Group by type
            by_type = {}
            for o in overrides.data:
                override_type = o.get('override_type', 'unknown')
                if override_type not in by_type:
                    by_type[override_type] = []
                by_type[override_type].append(o)
            
            print("\n  By Override Type:")
            for override_type, items in by_type.items():
                print(f"    {override_type}: {len(items)} overrides")
            
            print("\n  Sample Overrides:")
            for o in overrides.data[:10]:
                pattern = o.get('pattern_key', 'N/A')
                action = o.get('action_category', 'N/A')
                override_data = o.get('override_data', {})
                if isinstance(override_data, dict):
                    size_mult = override_data.get('size_multiplier', 'N/A')
                    print(f"    {pattern} | {action}: size_mult={size_mult}")
        else:
            print("  ⚠️  No pm_overrides found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        # Check if table exists or has different schema
        print(f"  💡 This might indicate a schema issue - checking...")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 5. TUNING-SPECIFIC ANALYSIS
    # ========================================================================
    print("\n🔧 5. Tuning-Specific Analysis:")
    print("-" * 80)
    try:
        # Check for tuning-related patterns
        tuning_patterns = [
            'pm.uptrend.S1.buy_flag',
            'pm.uptrend.S1.entry',
            'pm.uptrend.S2.buy_flag',
            'pm.uptrend.S2.entry',
            'pm.uptrend.S3.dx',
            'pm.uptrend.S3.trim'
        ]
        
        all_events = sb.table('pattern_trade_events').select('pattern_key, action_category, rr, pnl_usd').execute()
        
        tuning_stats = {}
        for pattern in tuning_patterns:
            pattern_events = [e for e in all_events.data if e.get('pattern_key') == pattern]
            if pattern_events:
                n = len(pattern_events)
                rrs = [e.get('rr') for e in pattern_events if e.get('rr') is not None]
                pnls = [e.get('pnl_usd') for e in pattern_events if e.get('pnl_usd') is not None]
                
                avg_rr = sum(rrs) / len(rrs) if rrs else 0
                avg_pnl = sum(pnls) / len(pnls) if pnls else 0
                total_pnl = sum(pnls) if pnls else 0
                
                n_min = 33
                status = "✅ Ready" if n >= n_min else f"⚠️  Need {n_min - n} more"
                
                tuning_stats[pattern] = {
                    'n': n,
                    'avg_rr': avg_rr,
                    'avg_pnl': avg_pnl,
                    'total_pnl': total_pnl,
                    'status': status
                }
        
        print("  Tuning Patterns Status:")
        for pattern, stats in tuning_stats.items():
            print(f"    {pattern}: n={stats['n']} {stats['status']}")
            print(f"      Avg RR: {stats['avg_rr']:.3f}, Avg PnL: ${stats['avg_pnl']:.2f}, Total PnL: ${stats['total_pnl']:.2f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

