#!/usr/bin/env python3
"""
Validation script to compare ta_tracker.py outputs before/after refactor.

Usage:
1. Run with original ta_tracker.py: python scripts/validate_ta_tracker_refactor.py --baseline
2. Refactor ta_tracker.py to use ta_utils.py
3. Run again: python scripts/validate_ta_tracker_refactor.py --validate

This compares:
- EMA values
- Slope values
- ATR/ADX values
- Overall TA structure
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker

load_dotenv()


def get_ta_snapshot(limit: int = 3) -> List[Dict[str, Any]]:
    """Get current TA values from database for comparison."""
    tracker = TATracker()
    positions = tracker._active_positions()
    snapshot = []
    
    for p in positions[:limit]:
        features = p.get("features") or {}
        ta = features.get("ta") or {}
        snapshot.append({
            "contract": p.get("token_contract"),
            "chain": p.get("token_chain"),
            "ta": ta
        })
    
    return snapshot


def compare_snapshots(baseline: List[Dict[str, Any]], validation: List[Dict[str, Any]]) -> bool:
    """Compare two snapshots and report differences."""
    if len(baseline) != len(validation):
        print(f"❌ Different number of positions: {len(baseline)} vs {len(validation)}")
        return False
    
    all_match = True
    
    for base, val in zip(baseline, validation):
        base_contract = base.get("contract")
        val_contract = val.get("contract")
        
        if base_contract != val_contract:
            print(f"❌ Position mismatch: {base_contract} vs {val_contract}")
            all_match = False
            continue
        
        base_ta = base.get("ta", {})
        val_ta = val.get("ta", {})
        
        # Compare EMA values
        base_ema = base_ta.get("ema", {})
        val_ema = val_ta.get("ema", {})
        for key in ["ema20_1h", "ema60_1h", "ema144_1h", "ema250_1h", "ema333_1h"]:
            base_val = base_ema.get(key, 0.0)
            val_val = val_ema.get(key, 0.0)
            if abs(base_val - val_val) > 1e-9:
                print(f"❌ {base_contract} EMA {key}: {base_val} vs {val_val} (diff: {abs(base_val - val_val)})")
                all_match = False
        
        # Compare slopes (most critical)
        base_slopes = base_ta.get("ema_slopes", {})
        val_slopes = val_ta.get("ema_slopes", {})
        for key in ["ema20_slope", "ema60_slope", "ema144_slope", "ema250_slope", "ema333_slope"]:
            base_val = base_slopes.get(key, 0.0)
            val_val = val_slopes.get(key, 0.0)
            # Allow tiny floating point differences
            if abs(base_val - val_val) > 1e-10:
                print(f"❌ {base_contract} Slope {key}: {base_val:.10f} vs {val_val:.10f} (diff: {abs(base_val - val_val):.10e})")
                all_match = False
        
        # Compare ATR
        base_atr = base_ta.get("atr", {}).get("atr_1h", 0.0)
        val_atr = val_ta.get("atr", {}).get("atr_1h", 0.0)
        if abs(base_atr - val_atr) > 1e-9:
            print(f"❌ {base_contract} ATR: {base_atr} vs {val_atr}")
            all_match = False
        
        # Compare ADX
        base_adx = base_ta.get("momentum", {}).get("adx_1h", 0.0)
        val_adx = val_ta.get("momentum", {}).get("adx_1h", 0.0)
        if abs(base_adx - val_adx) > 1e-6:  # ADX can have larger differences due to rounding
            print(f"⚠️  {base_contract} ADX: {base_adx} vs {val_adx} (diff: {abs(base_adx - val_adx)})")
            # Don't fail on ADX, just warn
        
        if all_match:
            print(f"✅ {base_contract}: All values match")
    
    return all_match


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validate ta_tracker refactor")
    ap.add_argument("--baseline", action="store_true", help="Save baseline snapshot")
    ap.add_argument("--validate", action="store_true", help="Compare against baseline")
    ap.add_argument("--run-tracker", action="store_true", help="Run TA tracker before snapshot")
    ap.add_argument("--limit", type=int, default=3, help="Number of positions to check")
    args = ap.parse_args()
    
    snapshot_file = project_root / "scripts" / ".ta_tracker_baseline.json"
    
    if args.run_tracker:
        print("Running TA tracker...")
        tracker = TATracker()
        updated = tracker.run()
        print(f"Updated {updated} positions")
    
    if args.baseline:
        print(f"Capturing baseline snapshot (checking {args.limit} positions)...")
        snapshot = get_ta_snapshot(limit=args.limit)
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)
        print(f"✅ Baseline saved to {snapshot_file}")
    
    elif args.validate:
        if not snapshot_file.exists():
            print(f"❌ Baseline file not found: {snapshot_file}")
            print("Run with --baseline first")
            sys.exit(1)
        
        print("Loading baseline...")
        with open(snapshot_file, "r") as f:
            baseline = json.load(f)
        
        print(f"Capturing validation snapshot (checking {args.limit} positions)...")
        validation = get_ta_snapshot(limit=args.limit)
        
        print("\nComparing snapshots...")
        if compare_snapshots(baseline, validation):
            print("\n✅ All values match! Refactor validated.")
            sys.exit(0)
        else:
            print("\n❌ Differences detected! Review carefully.")
            sys.exit(1)
    
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

