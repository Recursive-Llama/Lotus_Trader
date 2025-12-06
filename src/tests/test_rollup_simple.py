#!/usr/bin/env python3
"""Simple test for HL rollup"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from datetime import datetime, timedelta, timezone

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Check ticks
now = datetime.now(timezone.utc)
five_min_ago = now - timedelta(minutes=5)
ticks = sb.table('majors_trades_ticks').select('token, ts').gte('ts', five_min_ago.isoformat()).limit(10).execute()
print(f'Ticks found: {len(ticks.data)}')

# Test rollup
from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
rollup = OneMinuteRollup()

# Roll up 2 minutes ago
two_min_ago = now - timedelta(minutes=2)
bars = rollup.roll_minute(when=two_min_ago)
print(f'Bars written: {bars}')

# Check result
hl = sb.table('majors_price_data_ohlc').select('*').eq('chain', 'hyperliquid').order('timestamp', desc=True).limit(5).execute()
print(f'Hyperliquid bars: {len(hl.data)}')
for b in hl.data:
    print(f'  {b["token_contract"]}: ${b["close_usd"]} at {b["timestamp"]}')

