#!/usr/bin/env python3
"""
Analyze why first dip buy didn't trigger for S3 positions.

This script reads positions and shows the first dip buy diagnostics
to understand why the signal didn't fire.
"""

from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()


def analyze_first_dip_buy(
    position_id: Optional[int] = None,
    contract: Optional[str] = None,
    chain: Optional[str] = None,
    ticker: Optional[str] = None,
    timeframe: Optional[str] = None,
    stage: Optional[str] = None,
    all_positions: bool = False
) -> None:
    """Analyze first dip buy diagnostics for positions."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    sb: Client = create_client(url, key)
    
    # Build query
    query = (
        sb.table("lowcap_positions")
        .select("id,token_contract,token_chain,token_ticker,timeframe,features,status")
    )
    
    if position_id:
        query = query.eq("id", position_id)
    elif contract and chain:
        query = query.eq("token_contract", contract).eq("token_chain", chain)
        if timeframe:
            query = query.eq("timeframe", timeframe)
    elif ticker:
        query = query.eq("token_ticker", ticker.upper())
        if timeframe:
            query = query.eq("timeframe", timeframe)
    elif all_positions:
        query = query.in_("status", ["watchlist", "active"])
        if timeframe:
            query = query.eq("timeframe", timeframe)
    else:
        print("No query parameters provided")
        return
    
    res = query.limit(2000).execute()
    positions = res.data or []
    
    # Filter by stage if specified
    if stage:
        filtered = []
        for pos in positions:
            features = pos.get("features") or {}
            uptrend = features.get("uptrend_engine_v4") or {}
            current_state = uptrend.get("state", "")
            if current_state.upper() == stage.upper():
                filtered.append(pos)
        positions = filtered
    
    if not positions:
        print("No positions found")
        return
    
    print(f"\n{'='*80}")
    print(f"FIRST DIP BUY ANALYSIS - {len(positions)} position(s)")
    print(f"{'='*80}\n")
    
    for pos in positions:
        ticker = pos.get("token_ticker", "") or pos.get("token_contract", "?")[:20]
        timeframe = pos.get("timeframe", "?")
        features = pos.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        
        state = uptrend.get("state", "Unknown")
        price = float(uptrend.get("price", 0.0))
        
        # Get first dip buy diagnostics
        diagnostics = uptrend.get("diagnostics", {})
        first_dip_check = diagnostics.get("first_dip_buy_check", {})
        
        # Debug: Print full diagnostics structure if first_dip_check is missing
        if not first_dip_check and diagnostics:
            print(f"  Debug: Available diagnostics keys: {list(diagnostics.keys())}")
            print(f"  Debug: Full diagnostics: {json.dumps(diagnostics, indent=2, default=str)}")
        
        # Get S3 meta
        meta = features.get("uptrend_engine_v4_meta") or {}
        s3_start_ts = meta.get("s3_start_ts")
        first_dip_taken = meta.get("first_dip_buy_taken", False)
        
        # Get EMAs
        ema_vals = uptrend.get("ema", {})
        ema20 = float(ema_vals.get("ema20", 0.0))
        ema30 = float(ema_vals.get("ema30", 0.0))
        ema60 = float(ema_vals.get("ema60", 0.0))
        ema333 = float(ema_vals.get("ema333", 0.0))
        
        print(f"{ticker} ({timeframe}) - State: {state}")
        print(f"  Price: {price:.8f}")
        print(f"  EMAs: 20={ema20:.8f}, 30={ema30:.8f}, 60={ema60:.8f}, 333={ema333:.8f}")
        
        if s3_start_ts:
            print(f"  S3 Start: {s3_start_ts}")
        else:
            print(f"  ⚠️  No S3 start timestamp")
        
        if first_dip_taken:
            print(f"  ✅ First dip buy already taken")
        else:
            print(f"  ❌ First dip buy NOT taken")
        
        if not first_dip_check:
            print(f"  ⚠️  No first dip buy diagnostics found")
            print()
            continue
        
        # Show diagnostics
        reason = first_dip_check.get("reason")
        if reason:
            print(f"  ❌ Blocked: {reason}")
            print()
            continue
        
        bars_since_entry = first_dip_check.get("bars_since_entry")
        option1_ok = first_dip_check.get("option1_ema20_30", False)
        option2_ok = first_dip_check.get("option2_ema60", False)
        slope_ok = first_dip_check.get("slope_ok", False)
        ts_ok = first_dip_check.get("ts_ok", False)
        first_dip_flag = first_dip_check.get("first_dip_buy_flag", False)
        
        dist_ema20 = first_dip_check.get("dist_ema20", 0.0)
        dist_ema30 = first_dip_check.get("dist_ema30", 0.0)
        dist_ema60 = first_dip_check.get("dist_ema60", 0.0)
        halo_20_30 = first_dip_check.get("halo_20_30", 0.0)
        halo_60 = first_dip_check.get("halo_60", 0.0)
        
        ts_score = first_dip_check.get("ts_score", 0.0)
        ts_with_boost = first_dip_check.get("ts_with_boost", 0.0)
        sr_boost = first_dip_check.get("sr_boost", 0.0)
        
        ema144_slope = first_dip_check.get("ema144_slope", 0.0)
        ema250_slope = first_dip_check.get("ema250_slope", 0.0)
        
        print(f"\n  First Dip Buy Diagnostics:")
        print(f"    Bars since S3 entry: {bars_since_entry}")
        print(f"    First dip buy flag: {first_dip_flag}")
        print()
        
        print(f"  Option 1 (EMA20/30, bars 0-6):")
        print(f"    ✅ OK: {option1_ok}")
        if bars_since_entry is not None:
            print(f"    Bars check: {bars_since_entry} <= 6 = {bars_since_entry <= 6}")
        print(f"    Distance to EMA20: {dist_ema20:.8f} (halo: {halo_20_30:.8f})")
        print(f"    Distance to EMA30: {dist_ema30:.8f} (halo: {halo_20_30:.8f})")
        print(f"    Near EMA20/30: {dist_ema20 <= halo_20_30 or dist_ema30 <= halo_20_30}")
        print()
        
        print(f"  Option 2 (EMA60, bars 0-12):")
        print(f"    ✅ OK: {option2_ok}")
        if bars_since_entry is not None:
            print(f"    Bars check: {bars_since_entry} <= 12 = {bars_since_entry <= 12}")
        print(f"    Distance to EMA60: {dist_ema60:.8f} (halo: {halo_60:.8f})")
        print(f"    Near EMA60: {dist_ema60 <= halo_60}")
        print()
        
        print(f"  Slope Check:")
        print(f"    ✅ OK: {slope_ok}")
        print(f"    EMA144 slope: {ema144_slope:.6f} (need > 0.0)")
        print(f"    EMA250 slope: {ema250_slope:.6f} (need >= 0.0)")
        print(f"    Condition: EMA144_slope > 0.0 OR EMA250_slope >= 0.0")
        print()
        
        print(f"  TS + S/R Boost Check:")
        print(f"    ✅ OK: {ts_ok}")
        print(f"    TS score: {ts_score:.4f}")
        print(f"    S/R boost: {sr_boost:.4f}")
        print(f"    TS + boost: {ts_with_boost:.4f} (need >= 0.50)")
        print()
        
        # Summary
        if first_dip_flag:
            print(f"  ✅ FIRST DIP BUY WOULD TRIGGER")
        else:
            print(f"  ❌ FIRST DIP BUY BLOCKED:")
            reasons = []
            if bars_since_entry is not None:
                if bars_since_entry > 6 and not option2_ok:
                    reasons.append(f"Too many bars ({bars_since_entry} > 6 for EMA20/30, > 12 for EMA60)")
                elif bars_since_entry > 12:
                    reasons.append(f"Too many bars ({bars_since_entry} > 12)")
            if not option1_ok and not option2_ok:
                reasons.append("Price not near EMA20/30 or EMA60")
            if not slope_ok:
                reasons.append("Slope not OK (EMA144_slope <= 0.0 AND EMA250_slope < 0.0)")
            if not ts_ok:
                reasons.append(f"TS + boost too low ({ts_with_boost:.4f} < 0.50)")
            
            for reason in reasons:
                print(f"    - {reason}")
        
        print(f"\n{'='*80}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze first dip buy diagnostics")
    parser.add_argument("--position-id", type=int, help="Position ID")
    parser.add_argument("--contract", type=str, help="Token contract address")
    parser.add_argument("--chain", type=str, help="Token chain")
    parser.add_argument("--ticker", type=str, help="Token ticker")
    parser.add_argument("--timeframe", type=str, choices=["1m", "15m", "1h", "4h"], help="Timeframe")
    parser.add_argument("--stage", type=str, choices=["S0", "S1", "S2", "S3"], help="Filter by stage")
    parser.add_argument("--all", action="store_true", help="All positions")
    
    args = parser.parse_args()
    
    if not any([args.position_id, args.contract, args.ticker, args.all]):
        parser.print_help()
        sys.exit(1)
    
    if args.contract and not args.chain:
        print("Error: --chain required when using --contract")
        sys.exit(1)
    
    try:
        analyze_first_dip_buy(
            position_id=args.position_id,
            contract=args.contract,
            chain=args.chain,
            ticker=args.ticker,
            timeframe=args.timeframe,
            stage=args.stage,
            all_positions=args.all
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

