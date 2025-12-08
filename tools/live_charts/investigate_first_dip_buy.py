#!/usr/bin/env python3
"""
Investigate why first dip buy diagnostics are missing.

Checks:
1. When did engine last run? (check features.uptrend_engine_v4.ts)
2. What is prev_state? (should be "S3" for first dip buy check to run)
3. Is engine actually running?
4. Are there any early exits in the code path?
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


def investigate_first_dip_buy(
    position_id: Optional[int] = None,
    contract: Optional[str] = None,
    chain: Optional[str] = None,
    ticker: Optional[str] = None,
    timeframe: Optional[str] = None,
    stage: Optional[str] = None,
    all_positions: bool = False
) -> None:
    """Investigate why first dip buy diagnostics are missing."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    sb: Client = create_client(url, key)
    
    # Build query
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
    print(f"FIRST DIP BUY INVESTIGATION - {len(positions)} position(s)")
    print(f"{'='*80}\n")
    
    for pos in positions:
        ticker = pos.get("token_ticker", "") or pos.get("token_contract", "?")[:20]
        timeframe = pos.get("timeframe", "?")
        features = pos.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        position_updated_at = pos.get("updated_at")
        
        state = uptrend.get("state", "Unknown")
        prev_state = uptrend.get("prev_state", "")
        ts = uptrend.get("ts", "")
        meta = uptrend.get("meta", {})
        updated_at = meta.get("updated_at", "")
        
        # Get S3 meta
        position_meta = features.get("uptrend_engine_v4_meta") or {}
        s3_start_ts = position_meta.get("s3_start_ts")
        first_dip_taken = position_meta.get("first_dip_buy_taken", False)
        
        # Get diagnostics
        diagnostics = uptrend.get("diagnostics", {})
        first_dip_check = diagnostics.get("first_dip_buy_check", {})
        s3_buy_check = diagnostics.get("s3_buy_check", {})
        
        print(f"{ticker} ({timeframe})")
        print(f"  Status: {pos.get('status', '?')}")
        print(f"  Position updated_at: {position_updated_at}")
        print(f"  State: {state}")
        print(f"  Prev State: {prev_state or '(empty/bootstrap)'}")
        print(f"  Engine ts: {ts}")
        print(f"  Engine updated_at: {updated_at}")
        
        if s3_start_ts:
            print(f"  S3 Start: {s3_start_ts}")
            # Calculate time since S3 start
            try:
                start_dt = datetime.fromisoformat(s3_start_ts.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                time_since = now - start_dt
                print(f"  Time since S3 start: {time_since}")
                
                # Calculate bars for 1m timeframe
                if timeframe == "1m":
                    bars = int(time_since.total_seconds() / 60)
                    print(f"  Bars since S3 start (1m): {bars}")
                    print(f"  First dip buy window: EMA20/30 (bars 0-6), EMA60 (bars 0-12)")
                    print(f"  Still in window? EMA20/30: {bars <= 6}, EMA60: {bars <= 12}")
            except Exception as e:
                print(f"  Could not calculate time since: {e}")
        else:
            print(f"  ⚠️  No S3 start timestamp")
        
        print(f"  First dip buy taken: {first_dip_taken}")
        
        # Check if diagnostics exist
        print(f"\n  Diagnostics:")
        print(f"    Has first_dip_buy_check: {bool(first_dip_check)}")
        print(f"    Has s3_buy_check: {bool(s3_buy_check)}")
        print(f"    All diagnostic keys: {list(diagnostics.keys())}")
        
        if first_dip_check:
            print(f"    first_dip_buy_check keys: {list(first_dip_check.keys())}")
            reason = first_dip_check.get("reason")
            if reason:
                print(f"    Reason: {reason}")
        else:
            print(f"    ⚠️  No first_dip_buy_check diagnostics")
        
        # Analysis
        print(f"\n  Analysis:")
        
        # Check 1: Is prev_state "S3"?
        if prev_state != "S3":
            print(f"    ❌ prev_state is '{prev_state}', not 'S3'")
            print(f"       → First dip buy check only runs when prev_state == 'S3'")
            print(f"       → This means engine hasn't run since bootstrap, OR state changed")
        else:
            print(f"    ✅ prev_state is 'S3' (engine should check first dip buy)")
        
        # Check 2: Has engine run recently?
        if not ts:
            print(f"    ⚠️  No engine timestamp - engine may not have run")
        else:
            try:
                engine_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                time_since = now - engine_dt
                print(f"    Engine last ran: {time_since} ago")
                if time_since.total_seconds() > 300:  # 5 minutes
                    print(f"    ⚠️  Engine hasn't run in {time_since.total_seconds()/60:.1f} minutes")
            except Exception as e:
                print(f"    Could not parse engine timestamp: {e}")
        
        # Check 3: Are diagnostics missing?
        if not first_dip_check and prev_state == "S3":
            print(f"    ❌ Diagnostics missing even though prev_state == 'S3'")
            print(f"       → Possible causes:")
            print(f"         1. Check failed early (before diagnostics written)")
            print(f"         2. Code path didn't reach first_dip_buy check")
            print(f"         3. Diagnostics not being written to payload")
        
        print(f"\n{'='*80}\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Investigate first dip buy diagnostics")
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
        investigate_first_dip_buy(
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

