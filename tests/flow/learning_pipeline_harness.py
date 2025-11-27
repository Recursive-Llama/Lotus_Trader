"""
Learning Pipeline Harness (V5 Simplified)

Scenarios covered:
1. Base happy path (meets N_MIN and materializes overrides).
2. Missing-field replay (intent/mcap bucket missing → fallback handling).
3. Sparse events / decay fitting (below N_MIN so overrides stay suppressed).
4. DM lesson absence (miner invoked for DM module with no data).
5. Schema smoke (no injected data; ensure jobs no-op cleanly).
"""

import argparse
import asyncio
import logging
import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from src.intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import (
    run_aggregator,
)
from src.intelligence.lowcap_portfolio_manager.jobs.lesson_builder_v5 import mine_lessons
from src.intelligence.lowcap_portfolio_manager.jobs.override_materializer import (
    run_override_materializer,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
# Suppress noisy deps
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("LearningHarness")

SCENARIO_CHOICES = (
    "base",
    "missing-fields",
    "sparse-events",
    "dm-absence",
    "schema-smoke",
)

DEFAULT_TRADES = 40  # Meets N_MIN floor
SPARSE_TRADES = 20   # Below floor to test decay suppression
EXPECTED_EVENTS_PER_TRADE = 2  # Entry + Trim (close captured via facts)
DEFAULT_MIN_LESSON_N = 33


def expected_events(trade_count: int) -> int:
    return trade_count * EXPECTED_EVENTS_PER_TRADE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Learning pipeline harness")
    parser.add_argument(
        "--scenario",
        choices=SCENARIO_CHOICES,
        default="base",
        help="Scenario to execute (default: base)",
    )
    parser.add_argument(
        "--trades",
        type=int,
        help="Override number of synthetic trades to inject",
    )
    parser.add_argument(
        "--pattern-key",
        help="Optional pattern key to reuse (otherwise randomised)",
    )
    parser.add_argument(
        "--aggregator-limit",
        type=int,
        default=500,
        help="Number of strands for aggregator lookback",
    )
    return parser


async def setup_test_data(
    sb: Client,
    pattern_key: str,
    *,
    trade_count: int,
    inject_missing_fields: bool = False,
) -> None:
    """
    Inject N mock trades with Entry + Trim + Close.
    """
    print(
        f"\n[1/4] 🧪 Setting up {trade_count} trades "
        f"(Entry+Trim+Close) for pattern_key='{pattern_key}'..."
    )
    logger.info("Injecting mock trade strands...")
    
    base_time = datetime.now(timezone.utc) - timedelta(days=5)
    base_entry_context = {
        "curator": "test_curator",
        "chain": "solana",
        "mcap_bucket": "micro",
        "timeframe": "1h",
        "market_family": "meme",
        "intent": "scalp",
    }
    
    for i in range(trade_count):
        position_id = str(uuid.uuid4())
        trade_id = str(uuid.uuid4())
        
        rr = max(0.0, random.gauss(1.5, 0.5))
        ts = base_time + timedelta(hours=i * 4)

        entry_context = dict(base_entry_context)
        if inject_missing_fields:
            if i % 3 == 0:
                entry_context.pop("intent", None)
            if i % 5 == 0:
                entry_context.pop("mcap_bucket", None)

        # 1. Entry Action
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
                "trade_id": trade_id,
            },
            "created_at": ts.isoformat(),
        }
        sb.table("ad_strands").insert(entry_action).execute()

        # 2. Trim Action
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
                "trade_id": trade_id,
            },
            "created_at": (ts + timedelta(hours=1)).isoformat(),
        }
        sb.table("ad_strands").insert(trim_action).execute()

        # 3. Position Closed fact
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
                    "duration_hours": 4.0,
                },
            },
            "created_at": (ts + timedelta(hours=4)).isoformat(),
        }
        sb.table("ad_strands").insert(closed_strand).execute()
        
        if (i + 1) % 10 == 0 or (i + 1) == trade_count:
            print(f"  -> Injected {i + 1}/{trade_count} trades...")


async def verify_events(
    sb: Client,
    pattern_key: str,
    *,
    expected_count: int,
    expect_present: bool = True,
) -> bool:
    """Verify pattern_trade_events population."""
    res = (
        sb.table("pattern_trade_events")
        .select("count", count="exact")
        .eq("pattern_key", pattern_key)
        .execute()
    )
    count = res.count or 0
    print(f"  -> Events Verification: Found {count} events.")

    if not expect_present:
        if count == 0:
            print("  ✅ No events present (expected).")
            return True
        print(f"  ❌ FAIL: Expected zero events but found {count}")
        return False

    if count < expected_count:
        print(f"  ❌ FAIL: Expected {expected_count} events, found {count}")
        return False

    print("  ✅ Events Verified (Entry + Trim).")
    return True


async def verify_lessons(
    sb: Client,
    pattern_key: str,
    *,
    min_n: Optional[int] = DEFAULT_MIN_LESSON_N,
    expect_present: bool = True,
    require_depth2: bool = True,
) -> bool:
    """Verify learning_lessons mined."""
    res = (
        sb.table("learning_lessons")
        .select("*")
        .eq("pattern_key", pattern_key)
        .contains("scope_subset", {"chain": "solana"})
        .execute()
    )

    if not res.data:
        if expect_present:
            print("  ❌ FAIL: No lesson found for chain=solana slice")
            return False
        print("  ✅ No lessons present (expected).")
        return True
        
    lesson = res.data[0]
    stats = lesson.get("stats", {})
    print(f"  -> Lesson Found! ID={lesson.get('id')}")
    print(f"     N={lesson['n']}")
    print(f"     Avg RR={stats.get('avg_rr', 0.0):.2f}")
    print(f"     Edge Raw={stats.get('edge_raw', 0.0):.2f}")
    
    if min_n is not None and lesson["n"] < min_n:
        print(f"  ❌ FAIL: Lesson N below threshold ({lesson['n']} < {min_n})")
        return False
        
    print("  ✅ Single-dimension lesson verified.")

    if not require_depth2:
        return True

    res_deep = (
        sb.table("learning_lessons")
        .select("*")
        .eq("pattern_key", pattern_key)
        .contains("scope_subset", {"chain": "solana", "market_family": "meme"})
        .execute()
    )
    deep_lesson = next(
        (
            row
            for row in res_deep.data
            if row.get("scope_subset", {}).get("chain") == "solana"
            and row["scope_subset"].get("market_family") == "meme"
        ),
        None,
    )
    
    if not deep_lesson:
        print(
            "  ❌ FAIL: No Depth-2 lesson for chain=solana + market_family=meme",
        )
        return False
        
    print(f"  ✅ Depth-2 Lesson Verified! (N={deep_lesson['n']})")
    return True


async def verify_overrides(
    sb: Client,
    pattern_key: str,
    *,
    expect_present: bool = True,
    min_multiplier: float = 1.0,
) -> bool:
    """Verify pm_overrides materialized."""
    res = (
        sb.table("pm_overrides")
        .select("*")
        .eq("pattern_key", pattern_key)
        .contains("scope_subset", {"chain": "solana"})
        .execute()
    )

    if not res.data:
        if expect_present:
            print("  ❌ FAIL: No override found for chain=solana")
            return False
        print("  ✅ No overrides present (expected).")
        return True
        
    override = res.data[0]
    print(f"  -> Override Found! Multiplier={override['multiplier']:.2f}")
    
    if override["multiplier"] <= min_multiplier:
        print(
            f"  ⚠️ WARNING: Multiplier <= {min_multiplier:.2f}. "
            "Check edge calculation."
        )
        
    print("  ✅ Override Verified.")
    return True


async def verify_scope_defaults(sb: Client, pattern_key: str) -> bool:
    """Ensure missing-field replay still backfills required scope dims."""
    res = (
        sb.table("pattern_trade_events")
        .select("scope")
        .eq("pattern_key", pattern_key)
        .limit(20)
        .execute()
    )
    scopes: List[Dict[str, Any]] = [row.get("scope") or {} for row in res.data or []]
    fallback_hits = [scope for scope in scopes if scope.get("intent") == "unknown"]

    if not fallback_hits:
        print("  ❌ FAIL: Expected at least one scope with intent='unknown'")
        return False

    print(
        f"  ✅ Missing-field fallback verified "
        f"({len(fallback_hits)} rows with intent='unknown')."
    )
    return True


async def verify_dm_absence(sb: Client) -> bool:
    """Run miner for DM module to ensure it no-ops cleanly."""
    print("\n[5/5] 🧠 Running Miner (DM module, no data expected)...")
    dm_result = await mine_lessons(sb, module="dm")
    if dm_result == 0:
        print("  ✅ DM miner returned 0 lessons (expected).")
        return True

    print(f"  ❌ FAIL: DM miner created {dm_result} lessons unexpectedly.")
    return False


async def execute_pipeline(
    sb: Client,
    pattern_key: str,
    *,
    trade_count: int,
    aggregator_limit: int,
    inject_missing_fields: bool,
    lesson_min_n: Optional[int],
    expect_lessons: bool,
    expect_overrides: bool,
    require_depth2: bool,
) -> bool:
    await setup_test_data(
        sb,
        pattern_key,
        trade_count=trade_count,
        inject_missing_fields=inject_missing_fields,
    )

    print("\n[2/4] 📊 Running Aggregator (Event Logger)...")
    agg_res = await run_aggregator(sb, limit=aggregator_limit)
    print(f"  -> Aggregator Result: {agg_res}")

    if not await verify_events(
        sb,
        pattern_key,
        expected_count=expected_events(trade_count),
    ):
        return False

    print("\n[3/4] ⛏️  Running Miner (Lesson Builder)...")
    miner_res = await mine_lessons(sb, module="pm")
    print(f"  -> Miner Result: {miner_res} lessons created/updated")

    if not await verify_lessons(
        sb,
        pattern_key,
        min_n=lesson_min_n,
        expect_present=expect_lessons,
        require_depth2=require_depth2,
    ):
        return False

    print("\n[4/4] ⚖️  Running Judge (Override Materializer)...")
    mat_res = run_override_materializer(sb)
    print(f"  -> Materializer Result: {mat_res}")

    if not await verify_overrides(
        sb,
        pattern_key,
        expect_present=expect_overrides,
    ):
        return False

    return True


async def run_schema_smoke(
    sb: Client,
    pattern_key: str,
    *,
    aggregator_limit: int,
) -> bool:
    print("\n[Schema] ⛔ Skipping data injection (schema smoke).")

    print("\n[Schema] 📊 Running Aggregator...")
    agg_res = await run_aggregator(sb, limit=aggregator_limit)
    print(f"  -> Aggregator Result: {agg_res}")
    if not await verify_events(
        sb,
        pattern_key,
        expected_count=0,
        expect_present=False,
    ):
        return False

    print("\n[Schema] ⛏️  Running Miner (pm module)...")
    miner_res = await mine_lessons(sb, module="pm")
    print(f"  -> Miner Result: {miner_res}")
    if not await verify_lessons(
        sb,
        pattern_key,
        expect_present=False,
        require_depth2=False,
    ):
        return False

    print("\n[Schema] ⚖️  Running Judge (Override Materializer)...")
    mat_res = run_override_materializer(sb)
    print(f"  -> Materializer Result: {mat_res}")
    if not await verify_overrides(
        sb,
        pattern_key,
        expect_present=False,
    ):
        return False

    print("\n✅ Schema smoke completed without data.")
    return True


async def run_harness(args: argparse.Namespace) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return
        
    sb = create_client(url, key)
    pattern_key = args.pattern_key or f"TEST_V5_{uuid.uuid4().hex[:8]}"
    scenario = args.scenario
    
    print("\n=================================================================")
    print(f"🚀 STARTING V5 LEARNING PIPELINE HARNESS ({scenario})")
    print(f"Pattern Key: {pattern_key}")
    print("=================================================================")
    
    if scenario == "schema-smoke":
        success = await run_schema_smoke(
            sb,
            pattern_key,
            aggregator_limit=args.aggregator_limit,
        )
    else:
        trade_count = args.trades or DEFAULT_TRADES
        if scenario == "sparse-events" and args.trades is None:
            trade_count = SPARSE_TRADES

        inject_missing = scenario == "missing-fields"
        lesson_min_n = None if scenario == "sparse-events" else DEFAULT_MIN_LESSON_N
        expect_lessons = scenario != "sparse-events"
        expect_overrides = scenario != "sparse-events"
        require_depth2 = scenario != "sparse-events"

        success = await execute_pipeline(
            sb,
            pattern_key,
            trade_count=trade_count,
            aggregator_limit=args.aggregator_limit,
            inject_missing_fields=inject_missing,
            lesson_min_n=lesson_min_n,
            expect_lessons=expect_lessons,
            expect_overrides=expect_overrides,
            require_depth2=require_depth2,
        )

        if success and scenario == "missing-fields":
            success = await verify_scope_defaults(sb, pattern_key)

        if success and scenario == "dm-absence":
            success = await verify_dm_absence(sb)

    if success:
        print("\n=================================================================")
        print("🎉 HARNESS PASSED.")
        print("=================================================================\n")
    else:
        print("\n=================================================================")
        print("❌ HARNESS FAILED. See logs above for details.")
        print("=================================================================\n")
        

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    parser = build_parser()
    asyncio.run(run_harness(parser.parse_args()))

