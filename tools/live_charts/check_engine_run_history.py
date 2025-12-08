#!/usr/bin/env python3
"""
Check if engine ran multiple times for positions by looking at:
1. ad_strands table for uptrend_state_change events
2. Position updated_at timestamps
3. Features.uptrend_engine_v4.ts timestamps
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()


def check_engine_run_history(
    position_id: Optional[int] = None,
    contract: Optional[str] = None,
    chain: Optional[str] = None,
    ticker: Optional[str] = None,
    timeframe: Optional[str] = None,
    stage: Optional[str] = None,
    all_positions: bool = False
) -> None:
    """Check engine run history for positions."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    sb: Client = create_client(url, key)
    
    # Build query for positions
    query = (
        sb.table("lowcap_positions")
        .select("id,token_contract,token_chain,token_ticker,timeframe,features,status,updated_at")
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
    print(f"ENGINE RUN HISTORY CHECK - {len(positions)} position(s)")
    print(f"{'='*80}\n")
    
    for pos in positions:
        pid = pos.get("id")
        ticker = pos.get("token_ticker", "") or pos.get("token_contract", "?")[:20]
        timeframe = pos.get("timeframe", "?")
        features = pos.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        position_updated_at = pos.get("updated_at")
        
        state = uptrend.get("state", "Unknown")
        prev_state = uptrend.get("prev_state", "")
        engine_ts = uptrend.get("ts", "")
        
        # Get S3 start
        position_meta = features.get("uptrend_engine_v4_meta") or {}
        s3_start_ts = position_meta.get("s3_start_ts")
        
        print(f"{ticker} ({timeframe}) - Position ID: {pid}")
        print(f"  State: {state}, Prev State: {prev_state or '(empty)'}")
        print(f"  Engine ts: {engine_ts}")
        print(f"  Position updated_at: {position_updated_at}")
        if s3_start_ts:
            print(f"  S3 Start: {s3_start_ts}")
        
        # Check strands for uptrend_state_change events
        strands = []
        try:
            strands_res = (
                sb.table("ad_strands")
                .select("id,created_at,content")
                .eq("position_id", pid)
                .eq("kind", "uptrend_state_change")
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            strands = strands_res.data or []
            
            print(f"\n  Strands (uptrend_state_change): {len(strands)} found")
            if strands:
                print(f"  Most recent strand: {strands[0].get('created_at')}")
                print(f"  Oldest strand: {strands[-1].get('created_at')}")
                
                # Count by state
                state_counts = {}
                for s in strands:
                    content = s.get("content", {})
                    state_from_strand = content.get("state", "?")
                    state_counts[state_from_strand] = state_counts.get(state_from_strand, 0) + 1
                
                print(f"  State transitions: {state_counts}")
                
                # Show first few
                print(f"\n  First 5 strands:")
                for i, s in enumerate(strands[:5]):
                    content = s.get("content", {})
                    strand_state = content.get("state", "?")
                    strand_prev = content.get("prev_state", "")
                    print(f"    {i+1}. {s.get('created_at')}: {strand_prev} -> {strand_state}")
            else:
                print(f"  ⚠️  No uptrend_state_change strands found")
                print(f"     → This suggests engine may not be emitting events, or only ran once")
        except Exception as e:
            print(f"  Error checking strands: {e}")
            strands = []
        
        # Analyze timestamps
        print(f"\n  Timestamp Analysis:")
        try:
            if engine_ts:
                engine_dt = datetime.fromisoformat(engine_ts.replace("Z", "+00:00"))
                if s3_start_ts:
                    s3_dt = datetime.fromisoformat(s3_start_ts.replace("Z", "+00:00"))
                    time_diff = (engine_dt - s3_dt).total_seconds()
                    print(f"    Engine ran {time_diff:.0f} seconds after S3 start")
                    if time_diff < 300:  # Less than 5 minutes
                        print(f"    → Engine likely ran at bootstrap (within 5 min of S3 start)")
                    else:
                        print(f"    → Engine ran significantly after S3 start")
                
                now = datetime.now(timezone.utc)
                time_since = (now - engine_dt).total_seconds() / 60
                print(f"    Engine last ran {time_since:.1f} minutes ago")
                
                if timeframe == "1m":
                    expected_runs = int(time_since)
                    print(f"    Expected runs (1m): ~{expected_runs} times")
                    if expected_runs > 1 and len(strands) <= 1:
                        print(f"    ⚠️  Engine should have run ~{expected_runs} times but only {len(strands)} strands found")
        except Exception as e:
            print(f"    Error analyzing timestamps: {e}")
        
        # Conclusion
        print(f"\n  Conclusion:")
        if prev_state == "":
            print(f"    ❌ prev_state is empty → Engine hasn't run since bootstrap")
        elif prev_state == state:
            print(f"    ✅ prev_state == state → Engine ran but state didn't change")
        else:
            print(f"    ✅ prev_state != state → Engine ran and state changed")
        
        if len(strands) <= 1 and timeframe == "1m":
            print(f"    ⚠️  Only {len(strands)} strand(s) found for 1m position")
            print(f"       → Engine likely only ran once (at bootstrap)")
        
        print(f"\n{'='*80}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Check engine run history")
    parser.add_argument("--position-id", type=int, help="Position ID")
    parser.add_argument("--contract", type=str, help="Token contract address")
    parser.add_argument("--chain", type=str, help="Token chain")
    parser.add_argument("--ticker", type=str, help="Token ticker")
    parser.add_argument("--timeframe", type=str, choices=["1m", "15m", "1h", "4h"], help="Timeframe")
    parser.add_argument("--stage", type=str, choices=["S0", "S1", "2", "S3"], help="Filter by stage")
    parser.add_argument("--all", action="store_true", help="All positions")
    
    args = parser.parse_args()
    
    if not any([args.position_id, args.contract, args.ticker, args.all]):
        parser.print_help()
        sys.exit(1)
    
    if args.contract and not args.chain:
        print("Error: --chain required when using --contract")
        sys.exit(1)
    
    try:
        check_engine_run_history(
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

