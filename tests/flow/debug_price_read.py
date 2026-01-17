
import os
import sys
import logging
from supabase import create_client
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from src.intelligence.lowcap_portfolio_manager.data.price_data_reader import PriceDataReader

# Setup
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
reader = PriceDataReader(sb)
contract = "HYPE"
chain = "hyperliquid"
timeframe = "1h"

# 1. Direct Table Query (Baseline)
print(f"--- 1. Direct DB Query for {contract} ---")
res = sb.table("hyperliquid_price_data_ohlc").select("*").eq("token", contract).eq("timeframe", timeframe).limit(5).execute()
print(f"Direct Query Rows: {len(res.data)}")
if res.data:
    print(f"Sample Row: {res.data[0]}")

# 2. PriceDataReader Query
print(f"\n--- 2. PriceDataReader.fetch_recent_ohlc ---")
rows = reader.fetch_recent_ohlc(contract, chain, timeframe, limit=5)
print(f"Reader Rows: {len(rows)}")
if rows:
    print(f"Sample Row: {rows[0]}")
else:
    print("Reader returned NO rows.")

# 3. Latest Close
print(f"\n--- 3. PriceDataReader.latest_close ---")
latest = reader.latest_close(contract, chain, timeframe)
print(f"Latest Close: {latest}")
