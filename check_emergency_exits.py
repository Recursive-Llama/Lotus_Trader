#!/usr/bin/env python3
"""Check emergency_exit actions by timeframe to see if 1h positions are being processed too frequently."""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
if not url or not key:
    print('❌ Missing SUPABASE_URL or SUPABASE_KEY')
    sys.exit(1)

client = create_client(url, key)

# Get emergency_exit actions from last 24 hours
cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

print("="*80)
print("EMERGENCY_EXIT ACTIONS (Last 24 hours)")
print("="*80)
print()

results = (
    client.table('ad_strands')
    .select('kind,content,created_at,timeframe,symbol,position_id')
    .eq('kind', 'pm_action')
    .gte('created_at', cutoff)
    .order('created_at', desc=True)
    .limit(500)
    .execute()
)

emergency_exits = []
for r in results.data:
    content = r.get('content', {})
    decision_type = content.get('decision_type', '').lower()
    if decision_type == 'emergency_exit':
        emergency_exits.append({
            'created_at': r.get('created_at'),
            'timeframe': r.get('timeframe'),
            'symbol': r.get('symbol'),
            'position_id': r.get('position_id')
        })

print(f'Found {len(emergency_exits)} emergency_exit actions in last 24h\n')

# Group by timeframe
by_tf = {}
for ee in emergency_exits:
    tf = ee['timeframe'] or 'unknown'
    if tf not in by_tf:
        by_tf[tf] = []
    by_tf[tf].append(ee)

for tf in sorted(by_tf.keys()):
    items = by_tf[tf]
    print(f'{tf}: {len(items)} emergency_exits')
    
    # Group by position_id to see if same position is triggering multiple times
    by_position = {}
    for item in items:
        pos_id = item['position_id']
        if pos_id not in by_position:
            by_position[pos_id] = []
        by_position[pos_id].append(item)
    
    # Show positions with multiple emergency_exits
    multi_exits = {pid: items for pid, items in by_position.items() if len(items) > 1}
    if multi_exits:
        print(f'  ⚠️  {len(multi_exits)} position(s) with multiple emergency_exits:')
        for pos_id, pos_items in sorted(multi_exits.items(), key=lambda x: len(x[1]), reverse=True):
            symbol = pos_items[0]['symbol']
            print(f'    {symbol} (pos_id={pos_id}): {len(pos_items)} emergency_exits')
            # Show timestamps
            for item in sorted(pos_items, key=lambda x: x['created_at']):
                ts = item['created_at']
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    time_ago = datetime.now(timezone.utc) - dt
                    if time_ago.total_seconds() < 3600:
                        time_str = f"{int(time_ago.total_seconds() / 60)}m ago"
                    else:
                        time_str = f"{int(time_ago.total_seconds() / 3600)}h ago"
                except:
                    time_str = ts[:19]
                print(f'      - {time_str} ({ts[:19]})')
    else:
        print(f'  ✓ All positions have single emergency_exit')
    
    # Show first 10 timestamps to see frequency
    print(f'  Recent timestamps:')
    for item in sorted(items, key=lambda x: x['created_at'], reverse=True)[:10]:
        ts = item['created_at']
        symbol = item['symbol']
        print(f'    {symbol}: {ts[:19]}')
    
    print()

print("="*80)

