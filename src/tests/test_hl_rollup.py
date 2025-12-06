#!/usr/bin/env python3
"""
Isolated test for Hyperliquid WS rollup.
Run: python src/tests/test_hl_rollup.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from datetime import datetime, timedelta, timezone
import logging
logging.basicConfig(level=logging.INFO)


def test_hl_rollup():
    """Test Hyperliquid rollup pipeline."""
    print("Testing Hyperliquid rollup...")
    
    # 1. Test database connection
    print("\n1. Testing database connection...")
    try:
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        print("   ✓ Supabase connected")
    except Exception as e:
        print(f"   ✗ Supabase connection failed: {e}")
        return
    
    # 2. Check majors_trades_ticks table
    print("\n2. Checking majors_trades_ticks table...")
    try:
        result = sb.table("majors_trades_ticks").select("*").limit(0).execute()
        print("   ✓ majors_trades_ticks table exists")
    except Exception as e:
        print(f"   ✗ majors_trades_ticks table error: {e}")
        print("      This table stores raw ticks from Hyperliquid WS")
        return
    
    # 3. Check for recent ticks
    print("\n3. Checking for recent ticks...")
    try:
        five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        result = sb.table("majors_trades_ticks").select("token, ts, price").gte("ts", five_min_ago).limit(10).execute()
        if result.data:
            print(f"   ✓ Found {len(result.data)} recent ticks")
            for tick in result.data[:3]:
                print(f"      {tick['token']}: ${tick['price']} at {tick['ts']}")
        else:
            print("   ✗ No recent ticks found")
            print("      Is Hyperliquid WS running? Check HL_INGEST_ENABLED env var")
    except Exception as e:
        print(f"   ✗ Error checking ticks: {e}")
    
    # 4. Check majors_price_data_ohlc table
    print("\n4. Checking majors_price_data_ohlc table...")
    try:
        result = sb.table("majors_price_data_ohlc").select("*").limit(0).execute()
        print("   ✓ majors_price_data_ohlc table exists")
    except Exception as e:
        print(f"   ✗ majors_price_data_ohlc table error: {e}")
        return
    
    # 5. Check for recent OHLC bars
    print("\n5. Checking for recent OHLC bars...")
    try:
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        result = sb.table("majors_price_data_ohlc").select("token_contract, chain, timeframe, timestamp, close_usd").eq("timeframe", "1m").gte("timestamp", one_hour_ago).order("timestamp", desc=True).limit(10).execute()
        if result.data:
            print(f"   ✓ Found {len(result.data)} recent OHLC bars")
            for bar in result.data[:3]:
                print(f"      {bar['token_contract']} ({bar['chain']}): ${bar['close_usd']} at {bar['timestamp']}")
        else:
            print("   ✗ No recent OHLC bars found")
            print("      Rollup might not be running")
    except Exception as e:
        print(f"   ✗ Error checking OHLC: {e}")
    
    # 6. Test the rollup manually
    print("\n6. Testing rollup manually...")
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
        from datetime import datetime, timedelta, timezone
        
        rollup = OneMinuteRollup()
        
        # Try to roll up a recent minute (look back a bit more)
        now = datetime.now(timezone.utc)
        # Try rolling up 2 minutes ago to catch ticks
        two_min_ago = now - timedelta(minutes=2)
        
        print(f"      Rolling up minute ending at: {two_min_ago.replace(second=0, microsecond=0)}")
        bars_written = rollup.roll_minute(when=two_min_ago)
        print(f"   ✓ Rollup executed, {bars_written} bars written")
        
        if bars_written == 0:
            print("      No bars written - checking why...")
            # Check if ticks exist in that window
            start = two_min_ago.replace(second=0, microsecond=0)
            end = start + timedelta(minutes=1)
            tick_check = sb.table("majors_trades_ticks").select("token, ts").gte("ts", start.isoformat()).lt("ts", end.isoformat()).limit(5).execute()
            if tick_check.data:
                print(f"      Found {len(tick_check.data)} ticks in window - rollup should have worked")
            else:
                print(f"      No ticks found in window {start} to {end}")
    except Exception as e:
        import traceback
        print(f"   ✗ Rollup error: {e}")
        print(f"      {traceback.format_exc()}")
    
    # 7. Check distinct tokens in ticks
    print("\n7. Checking distinct tokens in ticks (last hour)...")
    try:
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        result = sb.table("majors_trades_ticks").select("token").gte("ts", one_hour_ago).execute()
        if result.data:
            tokens = list(set(r["token"] for r in result.data))
            print(f"   ✓ Found {len(tokens)} distinct tokens: {tokens}")
        else:
            print("   ✗ No tokens found in last hour")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n✓ HL rollup test complete")


if __name__ == "__main__":
    test_hl_rollup()

