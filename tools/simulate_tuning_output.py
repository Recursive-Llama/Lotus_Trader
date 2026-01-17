#!/usr/bin/env python3
"""
Simulate TuningMiner Output - What lessons and overrides would be created?
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
import math

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing credentials")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("SIMULATING TUNING MINER OUTPUT")
    print("=" * 80)
    
    # Get events with outcomes
    cutoff = (datetime.now() - timedelta(days=90)).isoformat()
    res = sb.table("pattern_episode_events")\
        .select("*")\
        .neq("outcome", "null")\
        .gte("timestamp", cutoff)\
        .execute()
    
    events = res.data or []
    print(f"\n📊 Events with outcomes: {len(events)}")
    
    if not events:
        print("  ⚠️  No events to process")
        return
    
    # Group by pattern_key
    by_pattern = {}
    for e in events:
        pattern = e.get('pattern_key', 'unknown')
        if pattern not in by_pattern:
            by_pattern[pattern] = []
        by_pattern[pattern].append(e)
    
    # Process each pattern
    for pattern, pattern_events in by_pattern.items():
        print(f"\n{'='*80}")
        print(f"PATTERN: {pattern}")
        print(f"{'='*80}")
        print(f"  Total events: {len(pattern_events)}")
        
        # Calculate rates (what TuningMiner does)
        acted = [e for e in pattern_events if e.get('decision') == 'acted']
        skipped = [e for e in pattern_events if e.get('decision') == 'skipped']
        
        success_acted = [e for e in acted if e.get('outcome') == 'success']
        failure_acted = [e for e in acted if e.get('outcome') == 'failure']
        success_skipped = [e for e in skipped if e.get('outcome') == 'success']
        failure_skipped = [e for e in skipped if e.get('outcome') == 'failure']
        
        n_acted = len(acted)
        n_skipped = len(skipped)
        n_misses = len(success_skipped)  # Skipped but would have succeeded
        n_fps = len(failure_acted)  # Acted but failed
        
        wr = len(success_acted) / n_acted if n_acted > 0 else 0.0
        fpr = len(failure_acted) / n_acted if n_acted > 0 else 0.0
        mr = len(success_skipped) / n_skipped if n_skipped > 0 else 0.0
        dr = len(failure_skipped) / n_skipped if n_skipped > 0 else 0.0
        
        print(f"\n  📊 RATES (What TuningMiner Calculates):")
        print(f"    Acted: {n_acted} events")
        print(f"      Success: {len(success_acted)} → WR (Win Rate) = {wr:.1%}")
        print(f"      Failure: {len(failure_acted)} → FPR (False Positive Rate) = {fpr:.1%}")
        print(f"    Skipped: {n_skipped} events")
        print(f"      Success (missed): {len(success_skipped)} → MR (Miss Rate) = {mr:.1%}")
        print(f"      Failure (dodged): {len(failure_skipped)} → DR (Dodge Rate) = {dr:.1%}")
        
        print(f"\n  🎯 PRESSURE CALCULATION:")
        print(f"    n_misses (skipped successes): {n_misses}")
        print(f"    n_fps (acted failures): {n_fps}")
        pressure = n_misses - n_fps
        print(f"    Pressure = n_misses - n_fps = {n_misses} - {n_fps} = {pressure}")
        
        if pressure > 0:
            print(f"    → Positive pressure: Too many MISSES (we're being too conservative)")
            print(f"    → Action: LOOSEN thresholds (lower TS, increase halo)")
        elif pressure < 0:
            print(f"    → Negative pressure: Too many FALSE POSITIVES (we're being too aggressive)")
            print(f"    → Action: TIGHTEN thresholds (raise TS, decrease halo)")
        else:
            print(f"    → Neutral pressure: Balanced")
        
        # Simulate what Override Materializer would do
        print(f"\n  🔧 OVERRIDE MATERIALIZER OUTPUT:")
        
        if pressure == 0:
            print(f"    No override created (pressure = 0)")
        else:
            # Drift parameters
            ETA = 0.005  # Learning rate from override_materializer.py
            
            # Calculate multipliers
            mult_threshold = math.exp(-ETA * pressure)
            mult_halo = math.exp(ETA * pressure)
            
            # Clamp [0.5, 2.0]
            mult_threshold = max(0.5, min(2.0, mult_threshold))
            mult_halo = max(0.5, min(2.0, mult_halo))
            
            print(f"    ETA (learning rate): {ETA}")
            print(f"    mult_threshold = exp(-ETA * pressure) = exp(-{ETA} * {pressure}) = {mult_threshold:.4f}")
            print(f"    mult_halo = exp(ETA * pressure) = exp({ETA} * {pressure}) = {mult_halo:.4f}")
            
            # Determine which overrides would be created
            if "S1" in pattern:
                print(f"\n    Would create overrides:")
                print(f"      - tuning_ts_min: {mult_threshold:.4f} (multiplies TS threshold)")
                print(f"      - tuning_halo: {mult_halo:.4f} (multiplies halo distance)")
                if abs(mult_threshold - 1.0) < 0.01:
                    print(f"      ⚠️  Threshold change too small (<1%), override skipped")
                if abs(mult_halo - 1.0) < 0.01:
                    print(f"      ⚠️  Halo change too small (<1%), override skipped")
            elif "S2" in pattern:
                print(f"\n    Would create overrides:")
                print(f"      - tuning_s2_ts_min: {mult_threshold:.4f}")
                print(f"      - tuning_s2_halo: {mult_halo:.4f}")
            elif "S3" in pattern and "dx" not in pattern.lower():
                print(f"\n    Would create overrides:")
                print(f"      - tuning_ts_min: {mult_threshold:.4f}")
                print(f"      - tuning_dx_min: {mult_threshold:.4f}")
        
        # Show what lesson would look like
        print(f"\n  📝 LEARNING LESSON (What gets written to DB):")
        print(f"    {{")
        print(f"      'module': 'pm',")
        print(f"      'pattern_key': '{pattern}',")
        print(f"      'action_category': 'tuning',")
        print(f"      'scope_subset': {{}} (global slice),")
        print(f"      'n': {len(pattern_events)},")
        print(f"      'stats': {{")
        print(f"        'wr': {wr:.3f},")
        print(f"        'fpr': {fpr:.3f},")
        print(f"        'mr': {mr:.3f},")
        print(f"        'dr': {dr:.3f},")
        print(f"        'n_acted': {n_acted},")
        print(f"        'n_skipped': {n_skipped},")
        print(f"        'n_misses': {n_misses},")
        print(f"        'n_fps': {n_fps},")
        print(f"        'n_total': {len(pattern_events)}")
        print(f"      }},")
        print(f"      'lesson_type': 'tuning_rates',")
        print(f"      'status': 'active'")
        print(f"    }}")
        
        # Simulate with n=15 (subset)
        print(f"\n  🔬 SIMULATION: What if N=15?")
        if len(pattern_events) >= 15:
            # Take first 15 events
            subset = pattern_events[:15]
            sub_acted = [e for e in subset if e.get('decision') == 'acted']
            sub_skipped = [e for e in subset if e.get('decision') == 'skipped']
            
            sub_success_acted = [e for e in sub_acted if e.get('outcome') == 'success']
            sub_failure_acted = [e for e in sub_acted if e.get('outcome') == 'failure']
            sub_success_skipped = [e for e in sub_skipped if e.get('outcome') == 'success']
            sub_failure_skipped = [e for e in sub_skipped if e.get('outcome') == 'failure']
            
            sub_n_misses = len(sub_success_skipped)
            sub_n_fps = len(sub_failure_acted)
            sub_pressure = sub_n_misses - sub_n_fps
            
            print(f"    With n=15:")
            print(f"      Acted: {len(sub_acted)}, Skipped: {len(sub_skipped)}")
            print(f"      Misses: {sub_n_misses}, FPs: {sub_n_fps}")
            print(f"      Pressure: {sub_pressure}")
            
            if sub_pressure != 0:
                sub_mult_threshold = max(0.5, min(2.0, math.exp(-ETA * sub_pressure)))
                sub_mult_halo = max(0.5, min(2.0, math.exp(ETA * sub_pressure)))
                print(f"      mult_threshold: {sub_mult_threshold:.4f}")
                print(f"      mult_halo: {sub_mult_halo:.4f}")
                print(f"    ⚠️  With n=15, rates are less reliable (small sample)")
                print(f"    ⚠️  Pressure could be noisy (one extra miss/FP changes pressure by 1)")
        else:
            print(f"    Not enough events to simulate n=15")
    
    print(f"\n{'='*80}")
    print("KEY INSIGHTS")
    print(f"{'='*80}")
    print("""
1. TuningMiner calculates RATES (WR, FPR, MR, DR) from episode decisions/outcomes
2. PRESSURE = n_misses - n_fps determines direction:
   - Positive → Loosen (we're missing opportunities)
   - Negative → Tighten (we're taking bad trades)
3. Override Materializer converts pressure to MULTIPLIERS:
   - mult_threshold = exp(-ETA * pressure) → adjusts TS/DX thresholds
   - mult_halo = exp(ETA * pressure) → adjusts halo distance
4. With lower N (e.g., n=15):
   - Rates are less reliable (small sample)
   - Pressure is more volatile (one event = ±1 pressure)
   - But still provides signal if pattern is consistent
5. The system learns: "In this scope, we should be more/less selective"
    """)

if __name__ == "__main__":
    main()

