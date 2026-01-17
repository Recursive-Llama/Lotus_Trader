#!/usr/bin/env python3
"""
Deep Dive: PM Strength Learning - Complete Analysis
- Code flow
- Data flow
- Edge calculation
- Multiplier mapping
- What's working, what's not
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
import math

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("PM STRENGTH LEARNING - COMPLETE DEEP DIVE")
    print("=" * 80)
    
    # ========================================================================
    # PART 1: UNDERSTAND THE FLOW
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 1: SYSTEM FLOW")
    print("=" * 80)
    
    print("""
    Flow:
    1. Position closes → position_closed strand created
    2. Pattern Scope Aggregator → reads strand, extracts:
       - pattern_key (e.g., "pm.uptrend.S1.entry")
       - action_category (e.g., "entry", "add", "trim", "exit")
       - scope (full context: chain, bucket, timeframe, regime, etc.)
       - rr (final trade R/R)
       - pnl_usd (realized PnL)
       - trade_id (links to parent trade)
    3. Writes to pattern_trade_events (one row per action)
    
    4. Lesson Builder (runs periodically):
       - Reads pattern_trade_events
       - Mines patterns with N >= 33 (recursive Apriori)
       - Calculates edge using 6-D Edge Math:
         * delta_rr = avg_rr - global_baseline_rr
         * reliability_score = 1 / (1 + adjusted_variance)
         * support_score = 1 - exp(-n / 50)
         * magnitude_score = sigmoid(avg_rr / 1.0)
         * time_score = 1.0
         * stability_score = 1 / (1 + variance)
         * edge_raw = delta_rr * reliability * (support + magnitude + time + stability) * decay_mult
       - Writes to learning_lessons (lesson_type='pm_strength')
    
    5. Override Materializer (runs periodically):
       - Reads learning_lessons (pm_strength)
       - Filters: |edge_raw| >= 0.05
       - Maps: multiplier = 1.0 + edge_raw (clamped [0.3, 3.0])
       - Writes to pm_overrides
    
    6. Runtime (PM Executor):
       - Calls apply_pattern_strength_overrides()
       - Finds matching overrides (scope_subset contained in current scope)
       - Blends multipliers using weighted average (specificity + confidence)
       - Applies to position_size_frac
    """)
    
    # ========================================================================
    # PART 2: CURRENT DATA STATE
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 2: CURRENT DATA STATE")
    print("=" * 80)
    
    # Get pattern_trade_events
    events = sb.table('pattern_trade_events').select('*').limit(1000).execute()
    
    if events.data:
        print(f"\n  Pattern Trade Events: {len(events.data)} total")
        
        # Clean pattern keys
        for e in events.data:
            pattern = e.get('pattern_key', '')
            if 'pattern_key=' in pattern:
                parts = pattern.split('pattern_key=')
                if len(parts) > 1:
                    e['clean_pattern'] = parts[1]
                else:
                    e['clean_pattern'] = pattern
            else:
                e['clean_pattern'] = pattern
        
        # Group by pattern+action
        by_pattern = {}
        for e in events.data:
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
        
        # Calculate global baseline
        all_rrs = []
        for e in events.data:
            if e.get('rr') is not None:
                all_rrs.append(e.get('rr'))
        global_baseline_rr = sum(all_rrs) / len(all_rrs) if all_rrs else 1.0
        
        print(f"  Global Baseline RR: {global_baseline_rr:.3f} (from {len(all_rrs)} events)")
        
        # Analyze each pattern
        print(f"\n  Pattern Analysis:")
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
            delta_rr = avg_rr - global_baseline_rr
            
            # Simulate edge calculation (simplified)
            variance = 0.0
            if len(rrs) > 1:
                mean = sum(rrs) / len(rrs)
                variance = sum((r - mean) ** 2 for r in rrs) / (len(rrs) - 1)
            
            # Edge components (simplified - no decay for now)
            reliability_score = 1.0 / (1.0 + variance + 0.25 / max(1, n))
            support_score = 1.0 - math.exp(-n / 50.0)
            magnitude_score = 1.0 / (1.0 + math.exp(-avg_rr / 1.0))
            time_score = 1.0
            stability_score = 1.0 / (1.0 + variance)
            
            integral = support_score + magnitude_score + time_score + stability_score
            edge_raw = delta_rr * reliability_score * integral * 1.0  # No decay for now
            
            multiplier = max(0.3, min(3.0, 1.0 + edge_raw))
            
            n_min = 33
            status = "✅ Ready" if n >= n_min else f"⚠️  Need {n_min - n} more"
            
            pattern_stats.append({
                'pattern': pattern,
                'action': action,
                'n': n,
                'unique_trades': unique_trades,
                'avg_rr': avg_rr,
                'delta_rr': delta_rr,
                'variance': variance,
                'reliability': reliability_score,
                'support': support_score,
                'edge_raw': edge_raw,
                'multiplier': multiplier,
                'status': status
            })
        
        pattern_stats.sort(key=lambda x: x['n'], reverse=True)
        
        for stat in pattern_stats:
            print(f"\n    {stat['pattern']} | {stat['action']}: n={stat['n']} (trades={stat['unique_trades']}) {stat['status']}")
            print(f"      Avg RR: {stat['avg_rr']:.3f}, Delta RR: {stat['delta_rr']:.3f}")
            print(f"      Variance: {stat['variance']:.3f}, Reliability: {stat['reliability']:.3f}")
            print(f"      Edge Raw: {stat['edge_raw']:.3f} → Multiplier: {stat['multiplier']:.3f}")
            if abs(stat['edge_raw']) < 0.05:
                print(f"      ⚠️  Edge too small (|{stat['edge_raw']:.3f}| < 0.05) → No override would be created")
    
    # ========================================================================
    # PART 3: LESSONS AND OVERRIDES
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 3: LESSONS AND OVERRIDES")
    print("=" * 80)
    
    # Check lessons
    lessons = sb.table('learning_lessons')\
        .select('*')\
        .eq('module', 'pm')\
        .eq('lesson_type', 'pm_strength')\
        .execute()
    
    print(f"\n  PM Strength Lessons: {len(lessons.data) if lessons.data else 0}")
    if lessons.data:
        for lesson in lessons.data[:5]:
            pattern = lesson.get('pattern_key', 'N/A')
            n = lesson.get('n', 0)
            stats = lesson.get('stats', {})
            if isinstance(stats, dict):
                edge_raw = stats.get('edge_raw', 'N/A')
                print(f"    {pattern}: n={n}, edge_raw={edge_raw}")
    
    # Check overrides
    overrides = sb.table('pm_overrides')\
        .select('*')\
        .not_.in_('action_category', ['tuning_ts_min', 'tuning_halo', 'tuning_dx_min', 'tuning_s2_ts_min', 'tuning_s2_halo', 'tuning_dx_atr_mult'])\
        .execute()
    
    print(f"\n  PM Strength Overrides: {len(overrides.data) if overrides.data else 0}")
    if overrides.data:
        for override in overrides.data[:5]:
            pattern = override.get('pattern_key', 'N/A')
            mult = override.get('multiplier', 'N/A')
            scope = override.get('scope_subset', {})
            print(f"    {pattern}: mult={mult}, scope={scope}")
    
    # ========================================================================
    # PART 4: ANALYSIS - WHAT'S WORKING, WHAT'S NOT
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 4: ANALYSIS - WHAT'S WORKING, WHAT'S NOT")
    print("=" * 80)
    
    print("""
    ✅ WHAT'S WORKING:
    1. Data collection: pattern_trade_events are being created
    2. Edge calculation: 6-D Edge Math is sophisticated (reliability, support, magnitude, stability, decay)
    3. Scope mining: Recursive Apriori finds all valid scope combinations
    4. Trade deduplication: Correctly deduplicates by trade_id (multiple actions per trade)
    
    ⚠️  POTENTIAL ISSUES:
    1. Using R/R instead of ROI:
       - R/R can be negative for profitable trades (if exit_price < entry_price due to trims)
       - R/R doesn't directly reflect profitability
       - Should we use ROI (rpnl_pct) instead?
    
    2. Edge threshold (0.05):
       - Only creates overrides if |edge_raw| >= 0.05
       - With negative R/R values, edge_raw is often negative
       - Negative edge_raw → multiplier < 1.0 → reduces sizing
       - But is this correct? Or should we use ROI?
    
    3. Multiplier mapping:
       - multiplier = 1.0 + edge_raw
       - If edge_raw = -0.5 → multiplier = 0.5 (50% sizing)
       - If edge_raw = +0.5 → multiplier = 1.5 (150% sizing)
       - Is this linear mapping appropriate?
    
    4. Blending vs Most Specific:
       - Current: Blends all matching overrides (weighted average)
       - With simulation-based tuning: We use most specific
       - Should PM Strength also use most specific? Or is blending OK here?
    
    5. N_MIN = 33:
       - Only 1 pattern meets threshold (S2.trim with n=52)
       - Most patterns need more data
       - Should we lower N_MIN? Or wait for more data?
    
    6. No lessons exist:
       - Despite S2.trim having n=52, no lessons found
       - Is Lesson Builder running?
       - Is there an issue with pattern key matching?
    """)
    
    # ========================================================================
    # PART 5: COMPARISON WITH TUNING
    # ========================================================================
    print("\n" + "=" * 80)
    print("PART 5: COMPARISON WITH TUNING SYSTEM")
    print("=" * 80)
    
    print("""
    Tuning System:
    - Uses episode events (opportunities, not outcomes)
    - Calculates rates (WR, FPR, MR, DR)
    - Simulates adjustments to find best solution
    - Uses most specific override
    
    PM Strength System:
    - Uses trade events (outcomes)
    - Calculates edge (6-D Edge Math)
    - Maps edge directly to multiplier
    - Blends matching overrides
    
    Key Differences:
    1. Tuning: Simulates to find optimal adjustment
       Strength: Direct mapping (edge → multiplier)
    
    2. Tuning: Most specific override wins
       Strength: Blends all matching overrides
    
    3. Tuning: Uses rates (WR, FPR, MR, DR)
       Strength: Uses edge (delta_rr * reliability * ...)
    
    Questions:
    - Should Strength also simulate? (probably not - sizing is simpler)
    - Should Strength use most specific? (maybe - consistency with tuning)
    - Should Strength use ROI instead of RR? (probably yes - same issue as tuning)
    """)
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

