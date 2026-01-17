#!/usr/bin/env python3
"""
Complete PM Tuning System Investigation
- Pattern Trade Events (for PM Strength)
- Pattern Episode Events (for PM Tuning)
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
    print("PM TUNING SYSTEM - COMPLETE INVESTIGATION")
    print("=" * 80)
    
    # ========================================================================
    # PART 1: PATTERN TRADE EVENTS (PM Strength Learning)
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 1: PATTERN TRADE EVENTS (PM Strength - Sizing)")
    print("=" * 80)
    
    print("\n📊 Pattern Trade Events Analysis:")
    print("-" * 80)
    try:
        # Get all events
        all_events = sb.table('pattern_trade_events').select('pattern_key, action_category, rr, pnl_usd, trade_id').execute()
        
        if all_events.data:
            # Extract pattern_key (remove module=pm|pattern_key= prefix)
            for e in all_events.data:
                pattern = e.get('pattern_key', '')
                if 'pattern_key=' in pattern:
                    # Extract actual pattern: "module=pm|pattern_key=uptrend.S1.entry" -> "uptrend.S1.entry"
                    parts = pattern.split('pattern_key=')
                    if len(parts) > 1:
                        e['clean_pattern'] = parts[1]
                    else:
                        e['clean_pattern'] = pattern
                else:
                    e['clean_pattern'] = pattern
            
            # Group by clean pattern and action
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
            
            pattern_stats.sort(key=lambda x: x['n'], reverse=True)
            
            print(f"  Total events: {len(all_events.data)}")
            print(f"  Unique patterns: {len(pattern_stats)}")
            print(f"  N_MIN threshold: 33")
            print(f"\n  Patterns (sorted by n):")
            for stat in pattern_stats:
                print(f"    {stat['pattern']} | {stat['action']}: n={stat['n']} (trades={stat['unique_trades']}) {stat['status']}")
                print(f"      Avg RR: {stat['avg_rr']:.3f}, Avg PnL: ${stat['avg_pnl']:.2f}, Total PnL: ${stat['total_pnl']:.2f}")
        else:
            print("  ⚠️  No pattern_trade_events found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # PART 2: PATTERN EPISODE EVENTS (PM Tuning Learning)
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 2: PATTERN EPISODE EVENTS (PM Tuning - Thresholds)")
    print("=" * 80)
    
    print("\n📊 Pattern Episode Events Analysis:")
    print("-" * 80)
    try:
        # Get all episode events
        all_episodes = sb.table('pattern_episode_events').select('*').execute()
        
        if all_episodes.data:
            print(f"  Total episode events: {len(all_episodes.data)}")
            
            # Group by pattern_key
            by_pattern = {}
            for e in all_episodes.data:
                pattern = e.get('pattern_key', 'unknown')
                decision = e.get('decision', 'unknown')
                outcome = e.get('outcome')
                
                if pattern not in by_pattern:
                    by_pattern[pattern] = {
                        'total': 0,
                        'acted': 0,
                        'skipped': 0,
                        'success_acted': 0,
                        'failure_acted': 0,
                        'success_skipped': 0,
                        'failure_skipped': 0,
                        'pending': 0
                    }
                
                by_pattern[pattern]['total'] += 1
                if decision == 'acted':
                    by_pattern[pattern]['acted'] += 1
                    if outcome == 'success':
                        by_pattern[pattern]['success_acted'] += 1
                    elif outcome == 'failure':
                        by_pattern[pattern]['failure_acted'] += 1
                elif decision == 'skipped':
                    by_pattern[pattern]['skipped'] += 1
                    if outcome == 'success':
                        by_pattern[pattern]['success_skipped'] += 1
                    elif outcome == 'failure':
                        by_pattern[pattern]['failure_skipped'] += 1
                
                if outcome is None:
                    by_pattern[pattern]['pending'] += 1
            
            # Calculate rates
            pattern_stats = []
            for pattern, data in by_pattern.items():
                n = data['total']
                n_acted = data['acted']
                n_skipped = data['skipped']
                n_misses = data['success_skipped']  # Skipped but would have succeeded
                n_fps = data['failure_acted']  # Acted but failed
                
                wr = data['success_acted'] / n_acted if n_acted > 0 else 0
                fpr = data['failure_acted'] / n_acted if n_acted > 0 else 0
                mr = data['success_skipped'] / n_skipped if n_skipped > 0 else 0
                dr = data['failure_skipped'] / n_skipped if n_skipped > 0 else 0
                
                n_min = 33
                status = "✅ Ready" if n >= n_min else f"⚠️  Need {n_min - n} more"
                
                pattern_stats.append({
                    'pattern': pattern,
                    'n': n,
                    'n_acted': n_acted,
                    'n_skipped': n_skipped,
                    'n_misses': n_misses,
                    'n_fps': n_fps,
                    'wr': wr,
                    'fpr': fpr,
                    'mr': mr,
                    'dr': dr,
                    'pending': data['pending'],
                    'status': status
                })
            
            pattern_stats.sort(key=lambda x: x['n'], reverse=True)
            
            print(f"  Unique patterns: {len(pattern_stats)}")
            print(f"  N_MIN threshold: 33")
            print(f"\n  Patterns (sorted by n):")
            for stat in pattern_stats:
                print(f"    {stat['pattern']}: n={stat['n']} {stat['status']}")
                print(f"      Acted: {stat['n_acted']} (WR={stat['wr']:.1%}, FPR={stat['fpr']:.1%})")
                print(f"      Skipped: {stat['n_skipped']} (MR={stat['mr']:.1%}, DR={stat['dr']:.1%})")
                print(f"      Misses: {stat['n_misses']}, FPs: {stat['n_fps']}")
                if stat['pending'] > 0:
                    print(f"      ⚠️  {stat['pending']} pending outcomes")
        else:
            print("  ⚠️  No pattern_episode_events found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # PART 3: LEARNING LESSONS
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 3: LEARNING LESSONS (Mined Patterns)")
    print("=" * 80)
    
    try:
        lessons = sb.table('learning_lessons').select('*').order('updated_at', desc=True).limit(100).execute()
        
        if lessons.data:
            print(f"  Total lessons: {len(lessons.data)} (showing last 100)")
            
            # Group by lesson_type
            by_type = {}
            for l in lessons.data:
                lesson_type = l.get('lesson_type', 'unknown')
                if lesson_type not in by_type:
                    by_type[lesson_type] = []
                by_type[lesson_type].append(l)
            
            print("\n  By Lesson Type:")
            for lesson_type, items in by_type.items():
                print(f"    {lesson_type}: {len(items)} lessons")
                
                # Show sample
                for lesson in items[:5]:
                    pattern = lesson.get('pattern_key', 'N/A')
                    n = lesson.get('n', 0)
                    stats = lesson.get('stats', {})
                    if isinstance(stats, dict):
                        if lesson_type == 'pm_strength':
                            edge_raw = stats.get('edge_raw', 'N/A')
                            avg_rr = stats.get('avg_rr', 'N/A')
                            print(f"      {pattern}: n={n}, avg_rr={avg_rr}, edge_raw={edge_raw}")
                        elif lesson_type == 'tuning_rates':
                            wr = stats.get('wr', 'N/A')
                            mr = stats.get('mr', 'N/A')
                            fpr = stats.get('fpr', 'N/A')
                            print(f"      {pattern}: n={n}, WR={wr}, MR={mr}, FPR={fpr}")
        else:
            print("  ⚠️  No learning_lessons found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================================================
    # PART 4: PM OVERRIDES
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 4: PM OVERRIDES (Actionable Rules)")
    print("=" * 80)
    
    try:
        overrides = sb.table('pm_overrides').select('*').limit(100).execute()
        
        if overrides.data:
            print(f"  Total overrides: {len(overrides.data)} (showing first 100)")
            
            # Group by action_category
            by_category = {}
            for o in overrides.data:
                category = o.get('action_category', 'unknown')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(o)
            
            print("\n  By Action Category:")
            for category, items in by_category.items():
                print(f"    {category}: {len(items)} overrides")
                
                # Show sample
                for override in items[:5]:
                    pattern = override.get('pattern_key', 'N/A')
                    mult = override.get('multiplier', 'N/A')
                    scope = override.get('scope_subset', {})
                    print(f"      {pattern}: mult={mult}, scope={scope}")
        else:
            print("  ⚠️  No pm_overrides found")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

