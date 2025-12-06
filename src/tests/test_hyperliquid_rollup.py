"""
Test Hyperliquid rollup flow: tick → 1m → 5m

Checks:
1. Are ticks being ingested?
2. Are 1m bars being created from ticks?
3. Are 5m bars being created from 1m bars?
4. How often is the rollup called?
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

load_dotenv()

from supabase import create_client

def main():
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY required")
        return
    
    sb = create_client(supabase_url, supabase_key)
    
    print("=" * 70)
    print("Hyperliquid Rollup Diagnostic")
    print("=" * 70)
    print()
    
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    five_minutes_ago = now - timedelta(minutes=5)
    
    # 1. Check ticks
    print("1. Checking ticks (majors_trades_ticks)...")
    ticks_result = sb.table("majors_trades_ticks").select(
        "token, ts"
    ).gte("ts", one_hour_ago.isoformat()).order("ts", desc=True).limit(10).execute()
    
    if ticks_result.data:
        print(f"   ✅ Found {len(ticks_result.data)} recent ticks")
        print(f"   Latest tick: {ticks_result.data[0]['ts']}")
        tokens = set(t['token'] for t in ticks_result.data)
        print(f"   Tokens: {', '.join(sorted(tokens))}")
    else:
        print("   ❌ No ticks found in last hour")
    
    print()
    
    # 2. Check 1m bars
    print("2. Checking 1m bars (majors_price_data_ohlc, timeframe='1m')...")
    bars_1m_result = sb.table("majors_price_data_ohlc").select(
        "token_contract, chain, timeframe, timestamp, close_usd"
    ).eq("chain", "hyperliquid").eq("timeframe", "1m").gte(
        "timestamp", one_hour_ago.isoformat()
    ).order("timestamp", desc=True).limit(20).execute()
    
    if bars_1m_result.data:
        print(f"   ✅ Found {len(bars_1m_result.data)} recent 1m bars")
        print(f"   Latest 1m bar: {bars_1m_result.data[0]['timestamp']}")
        tokens_1m = set(b['token_contract'] for b in bars_1m_result.data)
        print(f"   Tokens: {', '.join(sorted(tokens_1m))}")
        
        # Count bars in last 5 minutes
        bars_5min = [b for b in bars_1m_result.data if datetime.fromisoformat(b['timestamp'].replace('Z', '+00:00')) >= five_minutes_ago]
        print(f"   Bars in last 5 minutes: {len(bars_5min)}")
    else:
        print("   ❌ No 1m bars found in last hour")
    
    print()
    
    # 3. Check 5m bars
    print("3. Checking 5m bars (majors_price_data_ohlc, timeframe='5m')...")
    bars_5m_result = sb.table("majors_price_data_ohlc").select(
        "token_contract, chain, timeframe, timestamp, close_usd"
    ).eq("chain", "hyperliquid").eq("timeframe", "5m").gte(
        "timestamp", one_hour_ago.isoformat()
    ).order("timestamp", desc=True).limit(20).execute()
    
    if bars_5m_result.data:
        print(f"   ✅ Found {len(bars_5m_result.data)} recent 5m bars")
        print(f"   Latest 5m bar: {bars_5m_result.data[0]['timestamp']}")
        tokens_5m = set(b['token_contract'] for b in bars_5m_result.data)
        print(f"   Tokens: {', '.join(sorted(tokens_5m))}")
        
        # Check if we have a 5m bar in the last 10 minutes
        recent_5m = [b for b in bars_5m_result.data if datetime.fromisoformat(b['timestamp'].replace('Z', '+00:00')) >= (now - timedelta(minutes=10))]
        print(f"   5m bars in last 10 minutes: {len(recent_5m)}")
        if recent_5m:
            for bar in recent_5m[:5]:
                print(f"      - {bar['token_contract']}: {bar['timestamp']}")
    else:
        print("   ❌ No 5m bars found in last hour")
    
    print()
    
    # 4. Check rollup schedule
    print("4. Rollup Schedule Analysis...")
    print("   Expected schedule:")
    print("   - Tick → 1m: Every 60 seconds (majors_1m_rollup_job)")
    print("   - 1m → 5m: Every 5 minutes, aligned to :00, :05, :10, etc. (_wrap_rollup M5)")
    print()
    
    # Check if we're at a 5m boundary
    current_minute = now.minute
    is_boundary = current_minute % 5 == 0
    print(f"   Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   At 5m boundary: {'✅ Yes' if is_boundary else '❌ No'}")
    if not is_boundary:
        next_boundary_minute = ((current_minute // 5) + 1) * 5
        if next_boundary_minute >= 60:
            next_boundary_hour = now.hour + 1
            next_boundary_minute = 0
        else:
            next_boundary_hour = now.hour
        next_boundary = now.replace(hour=next_boundary_hour, minute=next_boundary_minute, second=0, microsecond=0)
        print(f"   Next 5m boundary: {next_boundary.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    print()
    
    # 5. Detailed check: Do we have enough 1m bars for a 5m rollup?
    print("5. Checking if we have enough 1m bars for 5m rollup...")
    if bars_1m_result.data:
        # Get all 1m bars from the last 5 minutes
        bars_for_5m = [b for b in bars_1m_result.data if datetime.fromisoformat(b['timestamp'].replace('Z', '+00:00')) >= five_minutes_ago]
        
        # Group by token
        tokens_bars = {}
        for bar in bars_for_5m:
            token = bar['token_contract']
            if token not in tokens_bars:
                tokens_bars[token] = []
            tokens_bars[token].append(bar)
        
        print(f"   Found 1m bars for {len(tokens_bars)} tokens in last 5 minutes:")
        for token, token_bars in sorted(tokens_bars.items()):
            print(f"      {token}: {len(token_bars)} bars")
            if len(token_bars) < 5:
                print(f"         ⚠️  Only {len(token_bars)} bars (need 5 for 5m rollup)")
            else:
                print(f"         ✅ Enough bars for 5m rollup")
    else:
        print("   ❌ No 1m bars to check")
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    has_ticks = bool(ticks_result.data)
    has_1m = bool(bars_1m_result.data)
    has_5m = bool(bars_5m_result.data)
    
    print(f"Ticks → 1m: {'✅ Working' if (has_ticks and has_1m) else '❌ Not working'}")
    print(f"1m → 5m: {'✅ Working' if (has_1m and has_5m) else '❌ Not working'}")
    
    if has_1m and not has_5m:
        print()
        print("⚠️  ISSUE: 1m bars exist but 5m bars don't!")
        print("   Possible causes:")
        print("   1. Rollup job not running or failing silently")
        print("   2. Boundary check failing (not at :00, :05, :10, etc.)")
        print("   3. Not enough 1m bars (need 5 bars per token)")
        print("   4. Bar already exists check preventing writes")
        print("   5. Error in rollup logic (check logs)")

if __name__ == "__main__":
    main()

