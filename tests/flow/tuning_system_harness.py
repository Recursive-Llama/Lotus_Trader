import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple

from supabase import create_client, Client
from dotenv import load_dotenv
from src.intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from src.intelligence.lowcap_portfolio_manager.jobs.tuning_miner import TuningMiner
from src.intelligence.lowcap_portfolio_manager.jobs.override_materializer import materialize_tuning_overrides

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()

HARNESS_TAG = "tuning_harness"
HARNESS_SCOPE = {"timeframe": "1h", "chain": "solana", "harness_tag": HARNESS_TAG}
HARNESS_S1_PATTERN = "module=pm|pattern_key=uptrend.S1.harness"
HARNESS_S3_PATTERN = "module=pm|pattern_key=uptrend.S3.harness"

async def setup_position(sb: Client, timeframe: str = "1h") -> str:
    """Create a test position."""
    # Cleanup existing
    try:
        sb.table("lowcap_positions").delete().eq("token_contract", "TUNE111111111111111111111111111111111111111").execute()
    except Exception:
        pass

    position_id = str(uuid.uuid4())
    trade_id = str(uuid.uuid4())
    
    pos = {
        "id": position_id,
        "status": "active",
        "token_ticker": "TUNE",
        "token_contract": "TUNE111111111111111111111111111111111111111", # Mock Address
        "token_chain": "solana",
        "timeframe": timeframe,
        "current_trade_id": trade_id,
        "total_quantity": 100.0,
        "avg_entry_price": 1.0,
        "features": {
            "uptrend_engine_v4": {
                "state": "S0",
                "price": 1.0,
                "ema": {"ema60": 1.0, "ema144": 1.0, "ema333": 1.0},
                "scores": {"ts": 50.0, "dx": 0.5, "edx": 0.5},
                "diagnostics": {
                    "buy_check": {"entry_zone_ok": False},
                    "s2_retest_check": {"entry_zone_ok": False}
                }
            },
            "pm_execution_history": {}
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    sb.table("lowcap_positions").insert(pos).execute()
    logger.info(f"Created test position {position_id}")
    return position_id

async def verify_episode_event(sb: Client, pattern_key: str, decision: str = None, outcome: str = None) -> bool:
    """Check if an episode event exists with specific attributes."""
    query = sb.table("pattern_episode_events").select("*").order("timestamp", desc=True).limit(1)
    
    if "%" in pattern_key:
        query = query.like("pattern_key", pattern_key)
    else:
        query = query.eq("pattern_key", pattern_key)
        
    if decision:
        query = query.eq("decision", decision)
    if outcome:
        query = query.eq("outcome", outcome)
        
    res = query.execute()
    events = res.data or []
    
    if events:
        evt = events[0]
        logger.info(f"✅ Found Event: {pattern_key} | Dec: {evt['decision']} | Out: {evt['outcome']}")
        return True
    else:
        # Debug: Print all events
        all_evts = sb.table("pattern_episode_events").select("*").order("timestamp", desc=True).limit(5).execute().data
        logger.info(f"DEBUG: All Recent Events: {all_evts}")
        logger.error(f"❌ Missing Event: {pattern_key} | Expected Dec: {decision} | Expected Out: {outcome}")
        return False


def _build_event(pattern_key: str, decision: str, outcome: str, idx: int) -> Dict[str, Any]:
    """Helper to build deterministic harness events."""
    ts = (datetime.now(timezone.utc) - timedelta(minutes=idx)).isoformat()
    return {
        "episode_id": f"harness_{pattern_key}_{idx}",
        "pattern_key": pattern_key,
        "scope": HARNESS_SCOPE,
        "decision": decision,
        "factors": {
            "ts_score": 50 + idx,
            "dx_score": 40 + idx,
            "edx_score": 30 + idx
        },
        "outcome": outcome,
        "timestamp": ts
    }


async def seed_tuning_phase_events(sb: Client) -> Tuple[str, str]:
    """Insert synthetic episode events so the miner can hit N_MIN."""
    logger.info("Seeding synthetic episode events for Phase 2/3 validation...")
    # Optional cleanup of prior harness rows
    try:
        sb.table("pattern_episode_events").delete().like("episode_id", "harness_%").execute()
    except Exception:
        pass

    s1_events = [_build_event(HARNESS_S1_PATTERN, "skipped", "success", i) for i in range(40)]
    s3_events = [_build_event(HARNESS_S3_PATTERN, "acted", "failure", i) for i in range(40)]
    sb.table("pattern_episode_events").insert(s1_events + s3_events).execute()
    logger.info("Inserted %d S1 events and %d S3 events", len(s1_events), len(s3_events))
    return HARNESS_S1_PATTERN, HARNESS_S3_PATTERN


def verify_tuning_lesson(sb: Client, pattern_key: str, expect_misses: bool) -> bool:
    res = (
        sb.table("learning_lessons")
        .select("stats,scope_subset,n")
        .eq("pattern_key", pattern_key)
        .eq("lesson_type", "tuning_rates")
        .eq("module", "pm")
        .execute()
    )
    lessons = res.data or []
    for lesson in lessons:
        scope = lesson.get("scope_subset") or {}
        if scope.get("harness_tag") != HARNESS_TAG:
            continue
        stats = lesson.get("stats") or {}
        n_misses = stats.get("n_misses", 0)
        n_fps = stats.get("n_fps", 0)
        if expect_misses and n_misses >= 33:
            logger.info("✅ Tuning lesson for %s captured %s misses", pattern_key, n_misses)
            return True
        if not expect_misses and n_fps >= 33:
            logger.info("✅ Tuning lesson for %s captured %s false positives", pattern_key, n_fps)
            return True
    logger.error("❌ Missing tuning lesson for %s (expect_misses=%s)", pattern_key, expect_misses)
    return False


def verify_tuning_override(sb: Client, pattern_key: str, action_category: str, comparator) -> bool:
    res = (
        sb.table("pm_overrides")
        .select("*")
        .eq("pattern_key", pattern_key)
        .eq("action_category", action_category)
        .execute()
    )
    rows = res.data or []
    for row in rows:
        scope = row.get("scope_subset") or {}
        if scope.get("harness_tag") != HARNESS_TAG:
            continue
        mult = float(row.get("multiplier", 1.0))
        if comparator(mult):
            logger.info("✅ Override %s for %s multiplier=%.3f", action_category, pattern_key, mult)
            return True
    logger.error("❌ Missing override %s for %s", action_category, pattern_key)
    return False

async def run_harness():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    sb = create_client(url, key)
    pm = PMCoreTick(timeframe="1h") # We don't need learning_system for this test
    
    print("\n=================================================================")
    print("🚀 STARTING TUNING SYSTEM HARNESS")
    print("=================================================================")

    try:
        # 1. Setup Position
        pid = await setup_position(sb)
        
        # 2. Test S1 Episode (Skipped -> Success)
        print("\n[Test 1] S1 Episode: Zone Contact -> Skipped -> S3 Success")
        
        # 2a. Trigger S1 Zone Contact (Skipped)
        now = datetime.now(timezone.utc)
        features_s1 = {
            "uptrend_engine_v4": {
            "state": "S1",
                "price": 0.98, # Dip below 1.0
                "ema": {"ema60": 1.0, "ema144": 0.9, "ema333": 0.8}, # EMA60 > 144 > 333
                "scores": {"ts": 45.0}, # Low TS -> Skip
            "diagnostics": {
                "buy_check": {
                        "entry_zone_ok": True, # TRIGGER
                        "halo": 0.05,
                        "ts_score": 45.0,
                        "ts_ok": False
                }
            },
                "buy_signal": False # Engine says No
            },
            "uptrend_episode_meta": {
                "prev_state": "S0" # Force transition detection
            },
            "pm_execution_history": {}
        }
        
        sb.table("lowcap_positions").update({"features": features_s1}).eq("id", pid).execute()
        pm.run() # Tick 1 (Window Open)
        
        await asyncio.sleep(1)
        
        # 2b. Close Window (Trigger Log)
        print("  -> Moving out of zone to close window...")
        # Fetch updated position to get the episode meta
        pos_res = sb.table("lowcap_positions").select("features").eq("id", pid).single().execute()
        features_updated = pos_res.data["features"]
        
        features_updated["uptrend_engine_v4"]["diagnostics"]["buy_check"]["entry_zone_ok"] = False
        
        sb.table("lowcap_positions").update({"features": features_updated}).eq("id", pid).execute()
        pm.run() # Tick 2 (Window Close -> Log)
        
        await asyncio.sleep(1)
        
        if not await verify_episode_event(sb, "%S1%", decision="skipped"):
            raise Exception("Failed to log S1 Skip")
            
        # 2c. Transition to S3 (Success)
        print("  -> Transitioning to S3...")
        # Fetch updated position to get the DB IDs of logged events
        pos_res = sb.table("lowcap_positions").select("features").eq("id", pid).single().execute()
        features_s3 = pos_res.data["features"]
        
        features_s3["uptrend_engine_v4"]["state"] = "S3"
        features_s3["uptrend_engine_v4"]["price"] = 1.20 # Rally
        features_s3["pm_execution_history"]["prev_state"] = "S1"
        
        sb.table("lowcap_positions").update({"features": features_s3}).eq("id", pid).execute()
        pm.run() # Tick 3
        
        await asyncio.sleep(1)
        # Verify Outcome (Should be success because S1 -> S3)
        # Note: pattern_key might be dynamic, let's query by decision to find the update
        if not await verify_episode_event(sb, "%S1%", decision="skipped", outcome="success"):
            raise Exception("Failed to update S1 Outcome to Success")
            
        # 3. Test S3 Retest (Skipped -> Success via Trim)
        print("\n[Test 2] S3 Retest: Band Contact -> Skipped -> Trim Success")
        
        # 3a. Trigger S3 Band Contact (Skipped)
        # Fetch current features to keep history
        pos_res = sb.table("lowcap_positions").select("features").eq("id", pid).single().execute()
        features_s3_dip = pos_res.data["features"]
        
        features_s3_dip["uptrend_engine_v4"]["state"] = "S3"
        features_s3_dip["uptrend_engine_v4"]["price"] = 0.85 # Dip below EMA144
        features_s3_dip["uptrend_engine_v4"]["scores"]["dx"] = 0.4
        features_s3_dip["pm_execution_history"]["prev_state"] = "S3" # Assuming we are already in S3 from prev step
        
        # But wait, previous step (2c) put us in S3. So meta should have s3_episode.
        # Let's check if s3_episode exists.
        if not features_s3_dip.get("uptrend_episode_meta", {}).get("s3_episode"):
             # Force transition if missing
             features_s3_dip["pm_execution_history"]["prev_state"] = "S1" 
        
        sb.table("lowcap_positions").update({"features": features_s3_dip}).eq("id", pid).execute()
        pm.run() # Tick 3 (Window Open)
        
        await asyncio.sleep(1)
        
        # Need to Close Window to trigger 'skipped' log?
        # For S3, skipping doesn't close window? 
        # If we stay in band, window stays open.
        # We need to leave band to close window and log 'skipped'.
        
        print("  -> Leaving band to close window (Log Skipped)...")
        pos_res = sb.table("lowcap_positions").select("features").eq("id", pid).single().execute()
        features_s3_close = pos_res.data["features"]
        features_s3_close["uptrend_engine_v4"]["price"] = 1.1 # Above EMA144
        
        sb.table("lowcap_positions").update({"features": features_s3_close}).eq("id", pid).execute()
        pm.run() # Tick 3b (Window Close)
        
        await asyncio.sleep(1)
        
        if not await verify_episode_event(sb, "%S3%", decision="skipped"):
            raise Exception("Failed to log S3 Retest Skip")
            
        # 3b. Inject Trim (Success)
        print("  -> Injecting Trim...")
        trim_ts = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        
        pos_res = sb.table("lowcap_positions").select("features").eq("id", pid).single().execute()
        features_trim = pos_res.data["features"]
        features_trim["pm_execution_history"]["last_trim"] = {"timestamp": trim_ts}
        
        sb.table("lowcap_positions").update({"features": features_trim}).eq("id", pid).execute()
        pm.run() # Tick 4
        
        await asyncio.sleep(1)
        # Verify Outcome (Should be success because Trim happened)
        if not await verify_episode_event(sb, "%S3%", decision="skipped", outcome="success"):
            raise Exception("Failed to update S3 Outcome to Success")

        # 4. Phase 2/3: Miner + Judge validation
        print("\n[Test 3] Phase 2/3: Miner + Drift Judge")
        s1_pattern, s3_pattern = await seed_tuning_phase_events(sb)
        miner = TuningMiner()
        miner.run()

        if not verify_tuning_lesson(sb, s1_pattern, expect_misses=True):
            raise Exception("Tuning lesson missing for S1 harness slice")
        if not verify_tuning_lesson(sb, s3_pattern, expect_misses=False):
            raise Exception("Tuning lesson missing for S3 harness slice")

        materialize_tuning_overrides(sb)

        if not verify_tuning_override(sb, s1_pattern, "tuning_ts_min", lambda m: m < 1.0):
            raise Exception("S1 tuning_ts_min override missing or not loosened")
        if not verify_tuning_override(sb, s1_pattern, "tuning_halo", lambda m: m > 1.0):
            raise Exception("S1 tuning_halo override missing or not loosened")
        if not verify_tuning_override(sb, s3_pattern, "tuning_ts_min", lambda m: m > 1.0):
            raise Exception("S3 tuning_ts_min override missing or not tightened")
        if not verify_tuning_override(sb, s3_pattern, "tuning_dx_min", lambda m: m > 1.0):
            raise Exception("S3 tuning_dx_min override missing or not tightened")

        print("\n=================================================================")
        print("🎉 TUNING SYSTEM HARNESS COMPLETE - ALL PASS")
        print("=================================================================\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: {e}")
        logger.error("Harness traceback:", exc_info=True)
    finally:
        # Cleanup?
        pass

if __name__ == "__main__":
    asyncio.run(run_harness())
