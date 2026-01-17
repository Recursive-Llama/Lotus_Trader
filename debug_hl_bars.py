
import os
import sys
import logging
from dotenv import load_dotenv
from supabase import create_client

# Setup basic logging to stdout
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug_hl")

def debug_hl_bars():
    # Load env
    load_dotenv()
    
    # Init Supabase (Service Role)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return
        
    print(f"Connecting to {url} with Service Role Key...")
    sb = create_client(url, key)
    
    # 1. Get HL active/watchlist positions
    print("\n1. Fetching Hyperliquid positions from lowcap_positions...")
    try:
        res = (
            sb.table("lowcap_positions")
            .select("token_contract,book_id,id,status")
            .eq("token_chain", "hyperliquid")
            .execute()
        )
        positions = res.data or []
        print(f"   Found {len(positions)} HL positions.")
    except Exception as e:
        print(f"   ❌ Failed to fetch positions: {e}")
        return

    # 2. Check bars for each
    print("\n2. Checking bars in hyperliquid_price_data_ohlc...")
    
    sample_limit = 5
    for i, p in enumerate(positions):
        token = p["token_contract"]
        book_id = p.get("book_id")
        
        # Test just the count for '1h' timeframe as sanity check
        timeframe = "1h"
        
        try:
            # Check with 'exact' count
            count_res = (
                sb.table("hyperliquid_price_data_ohlc")
                .select("ts", count="exact")
                .eq("token", token)
                .eq("timeframe", timeframe)
                .execute()
            )
            count = count_res.count if hasattr(count_res, "count") else 0
            
            # Also try fetching one row to see if we can read data
            data_res = (
                sb.table("hyperliquid_price_data_ohlc")
                .select("*")
                .eq("token", token)
                .eq("timeframe", timeframe)
                .limit(1)
                .execute()
            )
            has_data = len(data_res.data) > 0 if data_res.data else False
            
            status_icon = "✅" if count > 0 else "❌"
            print(f"   {status_icon} {token} ({book_id}): {count} bars (1h) - Can read data? {has_data}")
            
            if not has_data and i < 3:
                # Debug: check if token exists in DB with ANY timeframe
                any_res = (
                     sb.table("hyperliquid_price_data_ohlc")
                    .select("timeframe", count="exact")
                    .eq("token", token)
                    .execute()
                )
                print(f"      Any data for {token}? Count: {any_res.count}")

        except Exception as e:
            print(f"   ❌ Error checking {token}: {e}")

if __name__ == "__main__":
    debug_hl_bars()
