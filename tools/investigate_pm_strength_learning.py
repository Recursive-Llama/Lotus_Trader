#!/usr/bin/env python3
"""
Deep Dive into PM Strength Learning System
- What data we have
- What lessons exist
- What overrides exist
- How it works
- What's working, what could be improved
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
    print("PM STRENGTH LEARNING - DEEP DIVE")
    print("=" * 80)
    
    # ========================================================================
    # 1. PATTERN TRADE EVENTS (Data Source)
    # ========================================================================
    print("\n📊 1. Pattern Trade Events (Data Source)")
    print("-" * 80)
    
    try:
        # Get all events
        all_events = sb.table('pattern_trade_events').select('*').limit(1000).execute()
        
        if all_events.data:
            print(f"  Total events: {len(all_events.data)} (showing first 1000)")
            
            # Clean pattern keys
            for e in all_events.data:
                pattern = e.get('pattern_key', '')
                if 'pattern_key=' in pattern:
                    parts = pattern.split('pattern_key=')
                    if len(parts) > 1:
                        e['clean_pattern'] = parts[1]
                    else:
                        e['clean_pattern'] = pattern
                else:
                    e['clean_pattern'] = pattern
            
            # Group by pattern and action
            by_pattern = {}
            for e in all_events.data:
                pattern = e.get('clean_pattern', 'unknown')
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
                
                # Calculate edge components (simplified)
                global_baseline_rr = 1.0  # Would be calculated from all events
                delta_rr = avg_rr - global_baseline_rr
                
                n_min = 33
                status = "✅ Ready" if n >= n_min else f"⚠️  Need {n_min - n} more"
                
                pattern_stats.append({
                    'pattern': pattern,
                    'action': action,
                    'n': n,
                    'unique_trades': unique_trades,
                    'avg_rr': avg_rr,
                    'delta_rr': delta_rr,
                    'avg_pnl': avg_pnl,
                    'total_pnl': total_pnl,
                    'status': status
                })
            
            pattern_stats.sort(key=lambda x: x['n'], reverse=True)
            
            print(f"  Unique patterns: {len(pattern_stats)}")
            print(f"  N_MIN threshold: 33")
            print(f"\n  Patterns (sorted by n):")
            for stat in pattern_stats[:15]:
                print(f"    {stat['pattern']} | {stat['action']}: n={stat['n']} (trades={stat['unique_trades']}) {stat['status']}")
                print(f"      Avg RR: {stat['avg_rr']:.3f}, Delta RR: {stat['delta_rr']:.3f}, Avg PnL: ${stat['avg_pnl']:.2f}")
        else:
            print("  ⚠️  No pattern_trade_events found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 2. LEARNING LESSONS (PM Strength)
    # ========================================================================
    print("\n📊 2. Learning Lessons (PM Strength)")
    print("-" * 80)
    
    try:
        lessons = sb.table('learning_lessons')\
            .select('*')\
            .eq('module', 'pm')\
            .eq('lesson_type', 'pm_strength')\
            .order('updated_at', desc=True)\
            .limit(100)\
            .execute()
        
        if lessons.data:
            print(f"  Total PM Strength lessons: {len(lessons.data)}")
            
            # Analyze lessons
            for lesson in lessons.data[:10]:
                pattern = lesson.get('pattern_key', 'N/A')
                action = lesson.get('action_category', 'N/A')
                scope = lesson.get('scope_subset', {})
                n = lesson.get('n', 0)
                stats = lesson.get('stats', {})
                
                if isinstance(stats, dict):
                    avg_rr = stats.get('avg_rr', 'N/A')
                    edge_raw = stats.get('edge_raw', 'N/A')
                    delta_rr = stats.get('delta_rr', 'N/A')
                    decay_meta = stats.get('decay_meta', {})
                    decay_state = decay_meta.get('state', 'N/A') if isinstance(decay_meta, dict) else 'N/A'
                    
                    print(f"\n    {pattern} | {action}")
                    print(f"      Scope: {scope}")
                    print(f"      n={n}, avg_rr={avg_rr}, delta_rr={delta_rr}, edge_raw={edge_raw}")
                    print(f"      Decay: {decay_state}")
                    
                    # Calculate what multiplier would be
                    if isinstance(edge_raw, (int, float)):
                        multiplier = max(0.3, min(3.0, 1.0 + edge_raw))
                        print(f"      → Would create multiplier: {multiplier:.3f}")
        else:
            print("  ⚠️  No PM Strength lessons found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 3. PM OVERRIDES (PM Strength)
    # ========================================================================
    print("\n📊 3. PM Overrides (PM Strength)")
    print("-" * 80)
    
    try:
        # Get strength overrides (not tuning)
        overrides = sb.table('pm_overrides')\
            .select('*')\
            .not_.in_('action_category', ['tuning_ts_min', 'tuning_halo', 'tuning_dx_min', 'tuning_s2_ts_min', 'tuning_s2_halo', 'tuning_dx_atr_mult'])\
            .limit(100)\
            .execute()
        
        if overrides.data:
            print(f"  Total PM Strength overrides: {len(overrides.data)}")
            
            # Group by pattern
            by_pattern = {}
            for o in overrides.data:
                pattern = o.get('pattern_key', 'unknown')
                if pattern not in by_pattern:
                    by_pattern[pattern] = []
                by_pattern[pattern].append(o)
            
            print(f"  Unique patterns: {len(by_pattern)}")
            
            for pattern, items in list(by_pattern.items())[:10]:
                print(f"\n    {pattern}: {len(items)} overrides")
                for o in items[:3]:
                    action = o.get('action_category', 'N/A')
                    mult = o.get('multiplier', 'N/A')
                    scope = o.get('scope_subset', {})
                    conf = o.get('confidence_score', 'N/A')
                    print(f"      {action}: mult={mult}, scope={scope}, confidence={conf}")
        else:
            print("  ⚠️  No PM Strength overrides found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # 4. HOW IT WORKS - FLOW ANALYSIS
    # ========================================================================
    print("\n📊 4. How It Works - Flow Analysis")
    print("-" * 80)
    
    print("""
    Flow:
    1. Position closes → position_closed strand
    2. Pattern Scope Aggregator → extracts pattern_trade_events
    3. Lesson Builder → mines patterns, calculates edge, writes learning_lessons
    4. Override Materializer → filters lessons (edge >= 0.05), writes pm_overrides
    5. Runtime → apply_pattern_strength_overrides() applies multipliers
    
    Key Calculations:
    - edge_raw = delta_rr * reliability_score * integral * decay_multiplier
    - multiplier = 1.0 + edge_raw (clamped to [0.3, 3.0])
    - Only applies if |edge_raw| >= 0.05
    
    Current Issues to Investigate:
    - Is edge calculation correct?
    - Is multiplier mapping appropriate?
    - Should we use ROI instead of RR?
    - Is blending the right approach?
    - Are we capturing the right data?
    """)
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

