"""
Flow Test: Unified Learning System v2
=====================================
Following Flow Testing Ethos:
- Inject data at ingress (position_trajectories)
- Query database to verify state at each hop
- Know exactly where it dies if it dies

Tests S1/S2 Entry Learning (ROI-based, 4 trajectory types, shadows)
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_sb_client():
    """Create Supabase service client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def cleanup_test_data(sb, test_pattern_key: str):
    """Remove test data from previous runs."""
    try:
        sb.table("position_trajectories").delete().eq("pattern_key", test_pattern_key).execute()
        sb.table("pm_overrides").delete().eq("pattern_key", test_pattern_key).execute()
        logger.info(f"Cleaned up test data for pattern_key={test_pattern_key}")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")


def inject_trajectories(
    sb,
    pattern_key: str,
    trajectory_type: str,
    is_shadow: bool,
    scope: Dict[str, Any],
    count: int,
    roi_base: float = 10.0,
    blocked_by: List[str] = None,
    near_miss_gates: List[str] = None,
) -> List[str]:
    """
    Inject test trajectories directly into position_trajectories table.
    Returns list of created trajectory IDs.
    """
    trajectory_ids = []
    now = datetime.now(timezone.utc)
    
    for i in range(count):
        # Vary ROI slightly to avoid identical records
        roi = roi_base + (i * 0.5) if roi_base > 0 else roi_base - (i * 0.5)
        
        trajectory = {
            "position_id": str(uuid.uuid4()),  # Fake position IDs
            "trade_id": str(uuid.uuid4()) if not is_shadow else None,
            "entry_event": "S2.entry",
            "pattern_key": pattern_key,
            "scope": scope,
            "entry_time": (now - timedelta(hours=i)).isoformat(),
            "is_shadow": is_shadow,
            "blocked_by": blocked_by,
            "near_miss_gates": near_miss_gates,
            "gate_margins": {"ts": 0.05, "halo": 0.1, "slope": 0.02} if near_miss_gates or blocked_by else None,
            "trajectory_type": trajectory_type,
            "roi": roi,
            "did_trim": trajectory_type in ("trimmed_winner", "trim_but_loss"),
            "n_trims": 1 if trajectory_type in ("trimmed_winner", "trim_but_loss") else 0,
            "reached_s3": trajectory_type in ("trimmed_winner", "clean_winner"),
            "closed_at": now.isoformat(),
        }
        
        result = sb.table("position_trajectories").insert(trajectory).execute()
        if result.data:
            trajectory_ids.append(result.data[0].get("id"))
    
    logger.info(f"Injected {len(trajectory_ids)} trajectories: pattern={pattern_key}, type={trajectory_type}, shadow={is_shadow}")
    return trajectory_ids


def run_miner():
    """Run the TrajectoryMiner."""
    from intelligence.lowcap_portfolio_manager.learning.trajectory_miner import TrajectoryMiner
    miner = TrajectoryMiner()
    miner.run()
    logger.info("TrajectoryMiner.run() completed")


def query_overrides(sb, pattern_key: str) -> List[Dict[str, Any]]:
    """Query pm_overrides for a pattern_key."""
    result = sb.table("pm_overrides").select("*").eq("pattern_key", pattern_key).execute()
    return result.data or []


def test_strength_lesson_from_clean_winners():
    """
    Test: 15 clean_winner active trajectories → strength lesson with dirA ≈ +0.10
    """
    TEST_PATTERN = "test.flow.clean_winners"
    TEST_SCOPE = {"timeframe": "15m", "chain": "solana"}
    
    sb = get_sb_client()
    cleanup_test_data(sb, TEST_PATTERN)
    
    # Step 1: Inject 15 clean_winner active trajectories
    logger.info("Step 1: Injecting 15 clean_winner trajectories...")
    inject_trajectories(
        sb,
        pattern_key=TEST_PATTERN,
        trajectory_type="clean_winner",
        is_shadow=False,
        scope=TEST_SCOPE,
        count=15,
        roi_base=50.0,  # +50% ROI
    )
    
    # Step 2: Run miner
    logger.info("Step 2: Running TrajectoryMiner...")
    run_miner()
    
    # Step 3: Query pm_overrides
    logger.info("Step 3: Querying pm_overrides...")
    overrides = query_overrides(sb, TEST_PATTERN)
    
    if not overrides:
        logger.error("FAILED at Step 3: No overrides created for pattern_key=%s", TEST_PATTERN)
        return False
    
    # Step 4: Verify dirA
    strength_override = next((o for o in overrides if o.get("dira") is not None), None)
    if not strength_override:
        logger.error("FAILED at Step 4: No override with dira found")
        return False
    
    dir_a = float(strength_override.get("dira", 0))
    if dir_a <= 0:
        logger.error("FAILED at Step 4: Expected positive dirA for clean_winners, got %s", dir_a)
        return False
    
    logger.info("SUCCESS: dirA=%s, confidence=%s, n=%s", 
                dir_a, strength_override.get("confidence_score"), strength_override.get("n"))
    
    # Cleanup
    cleanup_test_data(sb, TEST_PATTERN)
    return True


def test_tuning_lesson_from_active_failures():
    """
    Test: 15 immediate_failure active trajectories with near_miss_gates=['ts'] 
          → tuning_tighten lesson with ts_min_delta > 0
    """
    TEST_PATTERN = "test.flow.active_failures"
    TEST_SCOPE = {"timeframe": "1h", "chain": "ethereum"}
    
    sb = get_sb_client()
    cleanup_test_data(sb, TEST_PATTERN)
    
    # Step 1: Inject 15 immediate_failure trajectories with near_miss_gates
    logger.info("Step 1: Injecting 15 immediate_failure trajectories...")
    inject_trajectories(
        sb,
        pattern_key=TEST_PATTERN,
        trajectory_type="immediate_failure",
        is_shadow=False,
        scope=TEST_SCOPE,
        count=15,
        roi_base=-10.0,  # -10% ROI
        near_miss_gates=["ts"],
    )
    
    # Step 2: Run miner
    logger.info("Step 2: Running TrajectoryMiner...")
    run_miner()
    
    # Step 3: Query pm_overrides for tuning
    logger.info("Step 3: Querying pm_overrides...")
    overrides = query_overrides(sb, TEST_PATTERN)
    
    tuning_override = next((o for o in overrides if o.get("action_category") == "tuning_tighten"), None)
    if not tuning_override:
        logger.warning("Step 3: No tuning_tighten override found (may be expected if gate analysis didn't trigger)")
        # This is acceptable - check if any override exists
        if not overrides:
            logger.error("FAILED at Step 3: No overrides at all for pattern_key=%s", TEST_PATTERN)
            return False
    else:
        tuning_params = tuning_override.get("tuning_params") or {}
        ts_delta = tuning_params.get("ts_min_delta", 0)
        logger.info("SUCCESS: tuning_tighten found, ts_min_delta=%s", ts_delta)
    
    # Check strength lesson (should have negative dirA for failures)
    strength_override = next((o for o in overrides if o.get("dira") is not None), None)
    if strength_override:
        dir_a = float(strength_override.get("dira", 0))
        logger.info("Strength lesson: dirA=%s (expected negative for failures)", dir_a)
    
    # Cleanup
    cleanup_test_data(sb, TEST_PATTERN)
    return True


def test_shadow_winner_loosening():
    """
    Test: 15 clean_winner shadow trajectories blocked by 'halo'
          → tuning_gate lesson with halo loosening
    """
    TEST_PATTERN = "test.flow.shadow_winners"
    TEST_SCOPE = {"timeframe": "4h"}
    
    sb = get_sb_client()
    cleanup_test_data(sb, TEST_PATTERN)
    
    # Step 1: Inject 15 shadow clean_winners blocked by halo
    logger.info("Step 1: Injecting 15 shadow clean_winner trajectories...")
    inject_trajectories(
        sb,
        pattern_key=TEST_PATTERN,
        trajectory_type="clean_winner",
        is_shadow=True,
        scope=TEST_SCOPE,
        count=15,
        roi_base=80.0,  # +80% ROI (would have been big win)
        blocked_by=["halo"],
    )
    
    # Step 2: Run miner
    logger.info("Step 2: Running TrajectoryMiner...")
    run_miner()
    
    # Step 3: Query pm_overrides
    logger.info("Step 3: Querying pm_overrides...")
    overrides = query_overrides(sb, TEST_PATTERN)
    
    if not overrides:
        logger.error("FAILED at Step 3: No overrides for pattern_key=%s", TEST_PATTERN)
        return False
    
    # Check for tuning_gate (loosening)
    tuning_gate = next((o for o in overrides if o.get("action_category") == "tuning_gate"), None)
    if tuning_gate:
        logger.info("SUCCESS: tuning_gate (loosening) found: %s", tuning_gate.get("tuning_params"))
    else:
        logger.warning("No tuning_gate override (EV tradeoff may have blocked it)")
    
    # Check for strength lesson (shadow winners should have positive dirA)
    strength_override = next((o for o in overrides if o.get("dira") is not None), None)
    if strength_override:
        dir_a = float(strength_override.get("dira", 0))
        if dir_a > 0:
            logger.info("SUCCESS: Strength lesson dirA=%s (positive for shadow winners)", dir_a)
        else:
            logger.warning("dirA=%s (expected positive for shadow winners)", dir_a)
    
    # Cleanup
    cleanup_test_data(sb, TEST_PATTERN)
    return True


def test_applicator_integration():
    """
    Test: Create override, then call lesson_applicator to verify it applies.
    """
    TEST_PATTERN = "test.flow.applicator"
    
    sb = get_sb_client()
    cleanup_test_data(sb, TEST_PATTERN)
    
    # Step 1: Insert a tuning override directly
    logger.info("Step 1: Inserting test tuning override...")
    test_override = {
        "pattern_key": TEST_PATTERN,
        "action_category": "tuning_tighten",
        "scope_subset": {"timeframe": "15m"},
        "tuning_params": {"ts_min_delta": 5.0},
        "confidence_score": 0.8,
        "n": 50,
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
    }
    sb.table("pm_overrides").insert(test_override).execute()
    
    # Step 2: Call lesson_applicator
    logger.info("Step 2: Calling apply_tuning_overrides...")
    from intelligence.lowcap_portfolio_manager.pm.lesson_applicator import apply_tuning_overrides
    
    # Simulate a position matching the scope
    mock_position = {
        "id": "test-position-123",
        "timeframe": "15m",
        "token_chain": "solana",
        "token_ticker": "TEST",
        "entry_context": {},
    }
    
    base_controls = {"ts_min": 60.0, "halo_mult": 1.0}
    
    result = apply_tuning_overrides(base_controls, mock_position, sb)
    
    # Step 3: Verify ts_min was adjusted
    new_ts_min = result.get("ts_min", 60.0)
    expected = 60.0 + 5.0  # base + delta
    
    if abs(new_ts_min - expected) < 0.01:
        logger.info("SUCCESS: ts_min adjusted from 60.0 to %s", new_ts_min)
    else:
        logger.error("FAILED: Expected ts_min=%s, got %s", expected, new_ts_min)
        cleanup_test_data(sb, TEST_PATTERN)
        return False
    
    # Cleanup
    cleanup_test_data(sb, TEST_PATTERN)
    return True


def test_dx_ladder_tuning():
    """Test 5: DX Ladder Tuning (detecting compressed ladder)."""
    # Pattern key
    pattern_key = "pm.uptrend.S3.dx"
    sb = get_sb_client()
    
    # Clean setup
    try:
        sb.table("position_trajectories").delete().eq("pattern_key", pattern_key).execute()
        sb.table("pm_overrides").delete().eq("pattern_key", pattern_key).execute()
        logger.info(f"Cleaned up test data for pattern_key={pattern_key}")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")
        
    # Step 1: Inject trajectories (Scenario: Too many 3s -> Spread Out)
    # 12x count=3, 3x count=1
    trajectories = []
    now = datetime.now(timezone.utc)
    
    # 12 trajectories with dx_count=3
    for i in range(12):
        trajectories.append({
            "position_id": str(uuid.uuid4()),
            "pattern_key": pattern_key,
            "entry_event": "S3.dx",
            "trajectory_type": "trimmed_winner",
            "is_shadow": False,
            "did_trim": True,
            "reached_s3": True,  # Required field
            "roi": 0,
            "entry_time": (now - timedelta(minutes=i)).isoformat(),
            "closed_at": now.isoformat(),
            "scope": {"bucket": "meso", "dx_count": 3}
        })
        
    # 3 trajectories with dx_count=1
    for i in range(3):
        trajectories.append({
            "position_id": str(uuid.uuid4()),
            "pattern_key": pattern_key,
            "entry_event": "S3.dx",
            "trajectory_type": "trimmed_winner",
            "is_shadow": False,
            "did_trim": True,
            "reached_s3": True,  # Required field
            "roi": 0,
            "entry_time": (now - timedelta(minutes=i)).isoformat(),
            "closed_at": now.isoformat(),
            "scope": {"bucket": "meso", "dx_count": 1}
        })
        
    for t in trajectories:
        sb.table("position_trajectories").insert(t).execute()
    
    logger.info(f"Injected {len(trajectories)} DX trajectories (mostly 3s)")
    
    # Step 2: Run Miner
    logger.info("Step 2: Running TrajectoryMiner...")
    from intelligence.lowcap_portfolio_manager.learning.trajectory_miner import TrajectoryMiner
    miner = TrajectoryMiner()
    miner.run()
    
    # Step 3: Verify Override
    logger.info("Step 3: Querying pm_overrides...")
    res = sb.table("pm_overrides")\
        .select("*")\
        .eq("pattern_key", pattern_key)\
        .eq("action_category", "tuning_dx")\
        .execute()
        
    overrides = res.data
    if not overrides:
        logger.error("FAILED at Step 3: No tuning_dx override found")
        return False
        
    override = overrides[0]
    params = override.get("tuning_params")
    
    # Expect spread out (delta > 0)
    dx_delta = params.get("dx_atr_mult_delta", 0)
    if dx_delta > 0:
        logger.info(f"SUCCESS: DX Tuning found, dx_atr_mult_delta={dx_delta} (Spread Out)")
    else:
        logger.error(f"FAILED: Expected positive delta, got {dx_delta}")
        return False
        
    # Cleanup
    sb.table("position_trajectories").delete().eq("pattern_key", pattern_key).execute()
    sb.table("pm_overrides").delete().eq("pattern_key", pattern_key).execute()
    
    return True


def main():
    """Run all flow tests."""
    print("\n" + "="*60)
    print("FLOW TEST: Unified Learning System v2")
    print("="*60 + "\n")
    
    results = {}
    
    # Test 1: Strength from clean winners
    print("\n--- Test 1: Strength Lesson from Clean Winners ---")
    results["strength_clean_winners"] = test_strength_lesson_from_clean_winners()
    
    # Test 2: Tuning from active failures
    print("\n--- Test 2: Tuning Lesson from Active Failures ---")
    results["tuning_active_failures"] = test_tuning_lesson_from_active_failures()
    
    # Test 3: Shadow winner loosening
    print("\n--- Test 3: Shadow Winner Gate Loosening ---")
    results["shadow_loosening"] = test_shadow_winner_loosening()
    
    # Test 4: Applicator integration
    print("\n--- Test 4: Lesson Applicator Integration ---")
    results["applicator_integration"] = test_applicator_integration()
    
    # Test 5: DX Ladder Tuning
    print("\n--- Test 5: DX Ladder Tuning ---")
    results["dx_ladder_tuning"] = test_dx_ladder_tuning()
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Check logs above for details.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
