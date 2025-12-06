#!/usr/bin/env python3
"""
Investigate State Transitions - Full Diagnostic

Checks:
1. Is uptrend engine running?
2. Are states being updated in database?
3. Is pm_core_tick detecting state changes?
4. Are transition strands being written?
"""

import sys
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta
import json

# Load environment
load_dotenv()

supabase_url = os.getenv("SUPABASE_URL", "")
supabase_key = os.getenv("SUPABASE_KEY", "")

if not supabase_url or not supabase_key:
    print("❌ SUPABASE_URL and SUPABASE_KEY required")
    sys.exit(1)

client = create_client(supabase_url, supabase_key)

print("="*80)
print("STATE TRANSITION INVESTIGATION")
print("="*80)
print()

# 1. Check if uptrend engine is updating positions
print("1. CHECKING IF UPTREND ENGINE IS UPDATING POSITIONS")
print("-"*80)

# Get positions with uptrend data
positions = (
    client.table("lowcap_positions")
    .select("id,token_ticker,timeframe,status,features,updated_at")
    .in_("status", ["watchlist", "active"])
    .eq("timeframe", "1m")
    .limit(10)
    .execute()
).data

print(f"Found {len(positions)} 1m positions")
print()

for pos in positions[:5]:
    ticker = pos.get("token_ticker", "?")
    features = pos.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}
    updated_at = pos.get("updated_at", "")
    
    state = uptrend.get("state", "?")
    prev_state = uptrend.get("prev_state", "?")
    price = uptrend.get("price", 0.0)
    
    print(f"  {ticker}:")
    print(f"    State: {state}")
    print(f"    Prev state (in payload): {prev_state}")
    print(f"    Price: {price:.6f}")
    print(f"    Updated at: {updated_at}")
    
    # Check meta for prev_state tracking
    meta = features.get("uptrend_engine_v4_meta") or {}
    meta_prev_state = meta.get("prev_state", "?")
    print(f"    Meta prev_state: {meta_prev_state}")
    
    # Check episode meta
    episode_meta = features.get("uptrend_episode_meta") or {}
    episode_prev_state = episode_meta.get("prev_state", "?")
    print(f"    Episode meta prev_state: {episode_prev_state}")
    print()

print()
print("2. CHECKING RECENT STATE CHANGES IN UPTREND_STATE_EVENTS")
print("-"*80)

# Check uptrend_state_events table (may not exist)
try:
    events = (
        client.table("uptrend_state_events")
        .select("token_contract,event_type,state,prev_state,ts")
        .order("ts", desc=True)
        .limit(20)
        .execute()
    )
    
    if events.data:
        print(f"Found {len(events.data)} recent events:")
        for e in events.data[:10]:
            prev = e.get("prev_state", "?")
            curr = e.get("state", "?")
            if prev != curr:
                print(f"  {e.get('token_contract', '?')[:8]}... | {prev} → {curr} | {e.get('ts', '?')}")
            else:
                print(f"  {e.get('token_contract', '?')[:8]}... | {curr} (no change) | {e.get('ts', '?')}")
    else:
        print("  ⚠️  No events in uptrend_state_events table (table may not exist or empty)")
except Exception as e:
    print(f"  ⚠️  uptrend_state_events table not found (this is OK, it's optional): {e}")

print()
print("3. CHECKING IF PM_CORE_TICK IS DETECTING STATE CHANGES")
print("-"*80)

# Check ad_strands for uptrend_stage_transition
transitions = (
    client.table("ad_strands")
    .select("kind,content,created_at")
    .eq("kind", "uptrend_stage_transition")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
)

if transitions.data:
    print(f"Found {len(transitions.data)} transition strands:")
    for t in transitions.data[:10]:
        c = t.get("content", {})
        from_s = c.get("from_state", "?")
        to_s = c.get("to_state", "?")
        print(f"  {from_s} → {to_s} | {t.get('created_at', '?')}")
else:
    print("  ❌ No uptrend_stage_transition strands found!")

print()
print("4. CHECKING STATE HISTORY FOR SAMPLE POSITIONS")
print("-"*80)

# Check if states have changed recently by comparing current vs previous
for pos in positions[:3]:
    ticker = pos.get("token_ticker", "?")
    features = pos.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}
    
    current_state = uptrend.get("state", "?")
    
    # Check episode meta for prev_state
    episode_meta = features.get("uptrend_episode_meta") or {}
    episode_prev_state = episode_meta.get("prev_state")
    
    print(f"  {ticker}:")
    print(f"    Current state: {current_state}")
    print(f"    Episode meta prev_state: {episode_prev_state}")
    
    if episode_prev_state and episode_prev_state != current_state:
        print(f"    ✅ STATE CHANGE DETECTED: {episode_prev_state} → {current_state}")
    elif episode_prev_state == current_state:
        print(f"    ⚠️  No change: {current_state} (same as prev_state)")
    else:
        print(f"    ⚠️  No prev_state in episode_meta (first run?)")
    print()

print()
print("5. CHECKING IF UPTREND ENGINE IS BEING CALLED")
print("-"*80)

# Check recent updated_at timestamps
recent_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
recent_updates = (
    client.table("lowcap_positions")
    .select("token_ticker,timeframe,updated_at,features")
    .in_("status", ["watchlist", "active"])
    .eq("timeframe", "1m")
    .gte("updated_at", recent_cutoff)
    .limit(10)
    .execute()
).data

if recent_updates:
    print(f"Found {len(recent_updates)} positions updated in last 10 minutes:")
    for p in recent_updates[:5]:
        ticker = p.get("token_ticker", "?")
        updated = p.get("updated_at", "?")
        features = p.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        state = uptrend.get("state", "?")
        print(f"  {ticker}: state={state}, updated={updated}")
else:
    print("  ⚠️  No positions updated in last 10 minutes")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print()
print("If you see:")
print("  - States in uptrend_engine_v4: ✅ Uptrend engine is writing states")
print("  - Events in uptrend_state_events: ✅ Uptrend engine is emitting events")
print("  - Transitions in ad_strands: ✅ PM Core Tick is detecting changes")
print("  - Recent updated_at timestamps: ✅ Positions are being updated")
print()
print("If you DON'T see:")
print("  - Recent updated_at: ❌ Uptrend engine may not be running")
print("  - State changes: ❌ States may not be changing (expected if conditions not met)")
print("  - Transition strands: ❌ PM Core Tick may not be detecting changes")

