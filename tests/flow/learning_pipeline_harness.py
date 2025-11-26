"""
Learning Pipeline Harness (V5 Simplified)

Tests the new architecture:
1. Events: Simulates a trade -> Writes to pattern_trade_events (Fact Table).
2. Miner: Runs Lesson Builder -> Scans events -> Writes to learning_lessons.
3. Judge: Runs Materializer -> Reads lessons -> Writes to pm_overrides.
"""

import asyncio
import logging
import os
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from supabase import create_client, Client

# Job imports
from src.intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import run_aggregator
from src.intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import mine_lessons
from src.intelligence.lowcap_portfolio_manager.jobs.override_materializer import run_override_materializer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Suppress httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("LearningHarness")

# Config
N_TRADES_TO_SIMULATE = 40 # Needs to be >= 33 to trigger N_MIN_SLICE
EXPECTED_EVENTS_PER_TRADE = 2 # Entry + Trim
TOTAL_EXPECTED_EVENTS = N_TRADES_TO_SIMULATE * EXPECTED_EVENTS_PER_TRADE

async def setup_test_data(sb: Client, pattern_key: str) -> None:
    """
    Injects N mock trades with Entry + Trim + Close.
    """
    print(f"\n[1/4] 🧪 Setting up {N_TRADES_TO_SIMULATE} test trades (Entry+Trim+Close) for pattern_key='{pattern_key}'...")
    logger.info("Injecting mock trade strands...")
    
    base_time = datetime.now(timezone.utc) - timedelta(days=5)
    
    entry_context = {
        "curator": "test_curator",
        "chain": "solana",
        "mcap_bucket": "micro",
        "timeframe": "1h",
        "market_family": "meme"
    }
    
    for i in range(N_TRADES_TO_SIMULATE):
        position_id = str(uuid.uuid4())
        trade_id = str(uuid.uuid4())
        
        # Create slightly varying R/R
        rr = max(0.0, random.gauss(1.5, 0.5))
        ts = base_time + timedelta(hours=i*4) 
        
        # 1. Entry Action (T+0)
        entry_action = {
            "kind": "pm_action",
            "module": "pm",
            "id": str(uuid.uuid4()),
            "position_id": position_id,
            "trade_id": trade_id,
            "content": {
                "pattern_key": pattern_key,
                "action_category": "entry",
                "scope": entry_context,
                "decision_type": "buy",
                "trade_id": trade_id
            },
            "created_at": ts.isoformat()
        }
        sb.table("ad_strands").insert(entry_action).execute()

        # 2. Trim Action (T+1h)
        trim_action = {
            "kind": "pm_action",
            "module": "pm",
            "id": str(uuid.uuid4()),
            "position_id": position_id,
            "trade_id": trade_id,
            "content": {
                "pattern_key": pattern_key,
                "action_category": "trim",
                "scope": entry_context,
                "decision_type": "sell",
                "trade_id": trade_id
            },
            "created_at": (ts + timedelta(hours=1)).isoformat()
        }
        sb.table("ad_strands").insert(trim_action).execute()

        # 3. Position Closed (Fact) (T+4h)
        closed_strand = {
            "kind": "position_closed",
            "module": "pm",
            "id": str(uuid.uuid4()),
            "parent_id": position_id,
            "content": {
                "position_id": position_id,
                "trade_id": trade_id,
                "pattern_key": pattern_key,
                "entry_context": entry_context,
                "trade_summary": {
                    "rr": rr,
                    "pnl_usd": rr * 100.0,
                    "duration_hours": 4.0
                }
            },
            "created_at": (ts + timedelta(hours=4)).isoformat()
        }
        sb.table("ad_strands").insert(closed_strand).execute()
        
        if (i+1) % 10 == 0:
            print(f"  -> Injected {i+1}/{N_TRADES_TO_SIMULATE} trades...")

async def verify_events(sb: Client, pattern_key: str) -> bool:
    """Verify pattern_trade_events populated."""
    res = sb.table("pattern_trade_events").select("count", count="exact").eq("pattern_key", pattern_key).execute()
    count = res.count
    print(f"  -> Events Verification: Found {count} events.")
    if count < TOTAL_EXPECTED_EVENTS:
        print(f"  ❌ FAIL: Expected {TOTAL_EXPECTED_EVENTS} events, found {count}")
        return False
    print("  ✅ Events Verified (Entry + Trim).")
    return True

async def verify_lessons(sb: Client, pattern_key: str) -> bool:
    """Verify learning_lessons mined."""
    # Check for the 'chain=solana' slice
    res = sb.table("learning_lessons").select("*")\
        .eq("pattern_key", pattern_key)\
        .contains("scope_subset", {"chain": "solana"})\
        .execute()
        
    if not res.data:
        print("  ❌ FAIL: No lesson found for chain=solana slice")
        return False
        
    lesson = res.data[0]
    stats = lesson.get("stats", {})
    print(f"  -> Lesson Found! ID={lesson.get('id')}")
    print(f"     N={lesson['n']}")
    print(f"     Avg RR={stats.get('avg_rr'):.2f}")
    print(f"     Edge Raw={stats.get('edge_raw'):.2f}")
    
    if lesson['n'] < 33:
        print("  ❌ FAIL: Lesson N is too low (miner didn't aggregate correctly)")
        return False
        
    print("  ✅ Single Dim Lesson Verified.")

    # Check for Depth 2 Lesson (chain=solana + market_family=meme)
    # The miner should have found this because all test trades share these
    res_deep = sb.table("learning_lessons").select("*")\
        .eq("pattern_key", pattern_key)\
        .contains("scope_subset", {"chain": "solana", "market_family": "meme"})\
        .execute()
        
    # Filter for exact match or subset containment
    deep_lesson = next((l for l in res_deep.data if l['scope_subset'].get('chain') == 'solana' and l['scope_subset'].get('market_family') == 'meme'), None)
    
    if not deep_lesson:
        print("  ❌ FAIL: No Depth-2 lesson found for chain=solana + market_family=meme")
        return False
        
    print(f"  ✅ Depth-2 Lesson Verified! (N={deep_lesson['n']})")
    return True

async def verify_overrides(sb: Client, pattern_key: str) -> bool:
    """Verify pm_overrides materialized."""
    res = sb.table("pm_overrides").select("*")\
        .eq("pattern_key", pattern_key)\
        .contains("scope_subset", {"chain": "solana"})\
        .execute()
        
    if not res.data:
        print("  ❌ FAIL: No override found for chain=solana")
        return False
        
    override = res.data[0]
    print(f"  -> Override Found! Multiplier={override['multiplier']:.2f}")
    
    if override['multiplier'] <= 1.0:
        print("  ⚠️ WARNING: Multiplier <= 1.0 (Expected > 1.0 for positive edge). Check edge calculation.")
        
    print("  ✅ Override Verified.")
    return True

async def run_harness():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return
        
    sb = create_client(url, key)
    pattern_key = f"TEST_V5_{uuid.uuid4().hex[:8]}"
    
    print("\n=================================================================")
    print("🚀 STARTING V5 LEARNING PIPELINE HARNESS")
    print("=================================================================")
    
    try:
        # 1. Setup
        await setup_test_data(sb, pattern_key)
        
        # 2. Run Aggregator (Event Logger)
        print("\n[2/4] 📊 Running Aggregator (Event Logger)...")
        # Process last 500 strands to cover our injected data
        agg_res = await run_aggregator(sb, limit=500)
        print(f"  -> Aggregator Result: {agg_res}")
        
        if not await verify_events(sb, pattern_key):
            return

        # 3. Run Miner (Lesson Builder)
        print("\n[3/4] ⛏️  Running Miner (Lesson Builder)...")
        miner_res = await mine_lessons(sb, module='pm')
        print(f"  -> Miner Result: {miner_res} lessons created/updated")
        
        if not await verify_lessons(sb, pattern_key):
            return

        # 4. Run Judge (Materializer)
        print("\n[4/4] ⚖️  Running Judge (Override Materializer)...")
        mat_res = run_override_materializer(sb)
        print(f"  -> Materializer Result: {mat_res}")
        
        if not await verify_overrides(sb, pattern_key):
            return
            
        print("\n=================================================================")
        print("🎉 HARNESS PASSED: V5 Learning Pipeline Verified.")
        print("=================================================================\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: {e}")
        logger.error("Harness traceback:", exc_info=True)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_harness())
