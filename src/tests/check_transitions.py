#!/usr/bin/env python3
"""
Quick check for recent state transitions.
Usage: python src/tests/check_transitions.py [--hours 24] [--timeframe 1m]
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

load_dotenv()

def check_transitions(hours=24, timeframe=None):
    """Check for recent state transitions."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY required")
        return
    
    client = create_client(supabase_url, supabase_key)
    
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    
    query = (
        client.table("ad_strands")
        .select("kind,content,created_at,symbol,timeframe")
        .eq("kind", "uptrend_stage_transition")
        .gte("created_at", cutoff)
        .order("created_at", desc=True)
    )
    
    if timeframe:
        query = query.eq("timeframe", timeframe)
    
    transitions = query.execute().data
    
    print("="*80)
    print(f"STATE TRANSITIONS (Last {hours} hours)")
    if timeframe:
        print(f"Timeframe: {timeframe}")
    print("="*80)
    print()
    
    if not transitions:
        print(f"  ⚠️  No transitions found in last {hours} hours")
        return
    
    print(f"Found {len(transitions)} transition(s):\n")
    
    for t in transitions:
        content = t.get("content", {})
        from_s = content.get("from_state", "?")
        to_s = content.get("to_state", "?")
        symbol = t.get("symbol", "?")
        tf = t.get("timeframe", "?")
        created = t.get("created_at", "?")
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            time_ago = datetime.now(timezone.utc) - dt
            if time_ago.total_seconds() < 3600:
                time_str = f"{int(time_ago.total_seconds() / 60)}m ago"
            else:
                time_str = f"{int(time_ago.total_seconds() / 3600)}h ago"
        except:
            time_str = created
        
        print(f"  {symbol} ({tf}): {from_s} → {to_s}  ({time_str})")
    
    print()
    print("="*80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check recent state transitions")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument("--timeframe", type=str, help="Filter by timeframe (1m, 15m, 1h, 4h)")
    args = parser.parse_args()
    
    check_transitions(hours=args.hours, timeframe=args.timeframe)




