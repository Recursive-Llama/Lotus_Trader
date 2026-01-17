
def test_dx_ladder_tuning():
    """Test 5: DX Ladder Tuning (detecting compressed ladder)."""
    # Pattern key
    pattern_key = "pm.uptrend.S3.dx"
    
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
    
    # 12 trajectories with dx_count=3
    for _ in range(12):
        trajectories.append({
            "position_id": f"test_dx_{uuid.uuid4().hex[:8]}",
            "pattern_key": pattern_key,
            "trajectory_type": "success",
            "is_shadow": False,
            "roi": 0,
            "entry_time": TEST_START_DATE,
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "scope": {"bucket": "meso", "dx_count": 3}
        })
        
    # 3 trajectories with dx_count=1
    for _ in range(3):
        trajectories.append({
            "position_id": f"test_dx_{uuid.uuid4().hex[:8]}",
            "pattern_key": pattern_key,
            "trajectory_type": "success",
            "is_shadow": False,
            "roi": 0,
            "entry_time": TEST_START_DATE,
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "scope": {"bucket": "meso", "dx_count": 1}
        })
        
    for t in trajectories:
        sb.table("position_trajectories").insert(t).execute()
    
    logger.info(f"Injected {len(trajectories)} DX trajectories (mostly 3s)")
    
    # Step 2: Run Miner
    logger.info("Step 2: Running TrajectoryMiner...")
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
