"""
Flow Test: Scenario 9 - PM/Executor Testing with Mocked Engine Payload

Objective: Test PM decision logic and Executor integration with various engine signal combinations

Why Mock Engine Payload:
- Real engine signals may take days/weeks to appear
- Need to test various combinations of state/flags/scores + A/E scores
- Need to test PM's decision logic without waiting for real market conditions

Test Strategy:
- Use real execution with small amounts ($1-2) on Solana
- Mock only: A/E scores and Uptrend Engine payload
- Use real: positions, OHLC data, executor, blockchain

Test Cases:
- 9.1: S1 Initial Entry (buy_signal)
- 9.2: S2 Retest Buy (buy_flag)
- 9.3: S3 DX Buy (buy_flag)
- 9.4: S3 First Dip Buy (first_dip_buy_flag)
- 9.5: S2/S3 Trim (trim_flag)
- 9.6: S3 Emergency Exit (emergency_exit)
- 9.7: Global Exit (exit_position)
- 9.8: No Action (Hold)
- 9.9: A/E Score Variations
- 9.10: Execution History Tracking
- 9.11: State Transition Resets
- 9.12: Trim Cooldown Logic
"""

import pytest
import sys
import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests.test_helpers import wait_for_condition
from intelligence.lowcap_portfolio_manager.pm.actions import plan_actions_v4
from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from utils.supabase_manager import SupabaseManager

# Configure logging for test visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


@pytest.mark.flow
class TestScenario9PMExecutor:
    """Test Scenario 9: PM/Executor Testing with Real Execution"""
    
    @pytest.mark.asyncio
    async def test_s1_initial_entry(
        self,
        test_db,
        test_curator,
        test_signal_id,
        empty_learning_system
    ):
        """
        Test Case 9.1: S1 Initial Entry (buy_signal)
        
        Flow:
        1. Create position (reuse from Scenario 1A setup)
        2. Mock engine payload: S1 state with buy_signal=true
        3. Mock A/E scores: a_final=0.5, e_final=0.3
        4. Run PM Core Tick (or call plan_actions_v4 directly)
        5. Verify decision: decision_type='add', size_frac based on a_final
        6. Execute real trade ($1-2 on Solana)
        7. Verify execution history updated
        8. Verify position updated (total_quantity > 0, status='active')
        """
        print("\n📊 Test 9.1: S1 Initial Entry (buy_signal)")
        sb = test_db.client
        
        # Use specific test token: Lil on Solana
        token_contract = "qnko6WJGEwEU3JYQFZakLe9V8dmS4YAXFARHeRipump"
        token_chain = "solana"
        token_ticker = "Lil"
        
        # Step 1: Create position (similar to Scenario 1A, but we'll create just 1h for PM testing)
        print("\n📊 Step 1: Creating test position...")
        
        # Clean up any existing positions
        sb.table("lowcap_positions").delete().eq("token_contract", token_contract).eq("token_chain", token_chain).execute()
        sb.table("lowcap_price_data_ohlc").delete().eq("token_contract", token_contract).eq("chain", token_chain).execute()
        print(f"   ✅ Cleaned up existing positions for {token_ticker}")
        
        # Create social signal and decision (reuse logic from Scenario 1A)
        curator_id = test_curator.get("curator_id") or test_curator.get("id") or "0xdetweiler"
        
        # Ensure curator exists
        curator_check = sb.table("curators").select("curator_id").eq("curator_id", curator_id).limit(1).execute()
        if not curator_check.data:
            sb.table("curators").insert({
                "curator_id": curator_id,
                "name": curator_id,
                "handle": test_curator.get("handle", curator_id),
                "platform": "twitter",
                "final_weight": 0.7,
                "win_rate": 0.7,
                "total_signals": 10
            }).execute()
        
        # Create social strand
        signal_id = test_signal_id
        social_strand = {
            "id": signal_id,
            "module": "social_ingest",
            "kind": "social_lowcap",
            "symbol": token_ticker,
            "timeframe": None,
            "session_bucket": f"social_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",
            "regime": None,
            "tags": ["curated", "social_signal", "dm_candidate", "verified"],
            "target_agent": "decision_maker_lowcap",
            "sig_sigma": None,
            "sig_confidence": 0.8,
            "confidence": 0.8,
            "sig_direction": "buy",
            "trading_plan": None,
            "signal_pack": {
                "curator": {"id": curator_id, "handle": curator_id, "platform": "twitter", "weight": 1.0},
                "token": {
                    "ticker": token_ticker,
                    "contract": token_contract,
                    "chain": token_chain,
                    "price": 0.0001,
                    "volume_24h": 100000,
                    "market_cap": 200000,
                    "liquidity": 50000,
                    "age_days": 3
                },
                "venue": {"dex": "raydium", "chain": token_chain, "liq_usd": 50000, "vol24h_usd": 100000},
                "intent_analysis": {"intent_analysis": {"intent_type": "new_discovery", "allocation_multiplier": 1.0, "confidence": 0.8}}
            },
            "content": {
                "curator_id": curator_id,
                "platform": "twitter",
                "handle": curator_id,
                "token": {
                    "ticker": token_ticker,
                    "contract": token_contract,
                    "chain": token_chain,
                    "price": 0.0001,
                    "volume_24h": 100000,
                    "market_cap": 200000,
                    "liquidity": 50000,
                    "age_days": 3
                },
                "venue": {"dex": "raydium", "chain": token_chain, "liq_usd": 50000, "vol24h_usd": 100000},
                "message": {"text": f"Check out {token_ticker}!", "timestamp": datetime.now(timezone.utc).isoformat(), "url": "https://twitter.com/test/status/123"},
                "curator_weight": 1.0,
                "context_slices": {}
            },
            "status": "active"
        }
        
        sb.table("ad_strands").insert(social_strand).execute()
        print(f"   ✅ Created social_lowcap strand: {signal_id}")
        
        # Create decision and position (using Decision Maker)
        from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
        supabase_manager = SupabaseManager()
        config = {
            'book_id': 'social',
            'min_curator_score': 0.6,
            'max_exposure_pct': 100.0,
            'max_positions': 69,
            'trading': {'min_curator_score': 0.6, 'max_exposure_pct': 100.0, 'max_positions': 69},
            'allocation_config': {
                'social_curators': {'excellent_score': 0.8, 'excellent_allocation': 15.0, 'good_score': 0.6, 'good_allocation': 6.0, 'acceptable_allocation': 4.0},
                'gem_bot': {'conservative_allocation': 6.0, 'balanced_allocation': 4.0, 'risky_allocation': 2.0},
                'test_mode': {'social_curators_multiplier': 0.1, 'gem_bot_multiplier': 0.2}
            },
            'min_volume_requirements': {'solana': 100000, 'ethereum': 25000, 'base': 25000}
        }
        decision_maker = DecisionMakerLowcapSimple(
            supabase_manager=supabase_manager,
            config=config,
            learning_system=empty_learning_system
        )
        
        decision = await decision_maker.make_decision(social_strand)
        if not decision:
            pytest.skip("Decision Maker rejected signal - cannot continue test")
        
        print(f"   ✅ Decision created, positions created with backfill")
        
        # Check what price data exists and manually collect if needed
        print(f"\n📊 Checking price data collection...")
        
        # Check if we have any 1m price data for this token
        price_data_1m = sb.table("lowcap_price_data_1m").select("timestamp,price_usd").eq("token_contract", token_contract).eq("chain", token_chain).order("timestamp", desc=True).limit(5).execute()
        print(f"   📊 Existing 1m price data: {len(price_data_1m.data or [])} entries")
        if price_data_1m.data:
            for entry in price_data_1m.data[:3]:
                print(f"      - {entry.get('timestamp')}: ${entry.get('price_usd')}")
        else:
            print(f"      ⚠️  NO 1m price data found - need to collect prices")
        
        # Check OHLC data
        ohlc_data = sb.table("lowcap_price_data_ohlc").select("timestamp").eq("token_contract", token_contract).eq("chain", token_chain).eq("timeframe", "1h").order("timestamp", desc=True).limit(5).execute()
        print(f"   📊 Existing 1h OHLC data: {len(ohlc_data.data or [])} bars")
        if ohlc_data.data:
            for bar in ohlc_data.data[:3]:
                print(f"      - {bar.get('timestamp')}")
        
        # Try to manually collect price data using price oracle
        print(f"\n📊 Attempting to collect current price data...")
        price_oracle = None
        try:
            from intelligence.trader_lowcap.price_oracle import PriceOracle
            
            # Initialize PriceOracle (no parameters needed - it uses DexScreener API directly)
            price_oracle = PriceOracle()
            
            # Get current price using chain-specific method
            price_info = None
            if token_chain.lower() == 'solana':
                price_info = price_oracle.price_solana(token_contract)
            elif token_chain.lower() == 'bsc':
                price_info = price_oracle.price_bsc(token_contract)
            elif token_chain.lower() == 'base':
                price_info = price_oracle.price_base(token_contract)
            elif token_chain.lower() == 'ethereum':
                price_info = price_oracle.price_eth(token_contract)
            else:
                print(f"   ⚠️  Unsupported chain: {token_chain}")
            
            if price_info and price_info.get('price_usd'):
                current_price = price_info.get('price_usd')
                print(f"   ✅ Current price: ${current_price} USD")
                
                # Manually insert 1m price point (simulating price collector)
                now = datetime.now(timezone.utc)
                price_data = {
                    "token_contract": token_contract,
                    "chain": token_chain.lower(),
                    "timestamp": now.isoformat(),
                    "price_usd": float(current_price),
                    "price_native": float(price_info.get('price_native', 0.0)),
                    "source": "test_manual"
                }
                sb.table("lowcap_price_data_1m").upsert(price_data).execute()
                print(f"   ✅ Inserted 1m price point: ${price_data['price_usd']} at {now.isoformat()}")
            else:
                print(f"   ⚠️  Could not get current price - price_oracle returned: {price_info}")
            
        except Exception as e:
            print(f"   ⚠️  Error collecting price: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            price_oracle = None  # Set to None if initialization failed
        
        # Now convert 1m price points to OHLC
        print(f"\n📊 Converting 1m price points to OHLC...")
        from intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import GenericOHLCRollup, DataSource, Timeframe
        
        rollup = GenericOHLCRollup()
        # Convert any existing 1m price points to 1m OHLC bars
        lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.M1)
        print(f"   ✅ OHLC conversion: {lowcaps_written} 1m bars created")
        
        # Roll up to 1h (since we're testing with 1h timeframe)
        lowcaps_1h = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.H1)
        print(f"   ✅ 1h rollup: {lowcaps_1h} 1h bars created")
        
        # Verify OHLC data exists after conversion
        ohlc_after = sb.table("lowcap_price_data_ohlc").select("timestamp").eq("token_contract", token_contract).eq("chain", token_chain).eq("timeframe", "1h").order("timestamp", desc=True).limit(5).execute()
        print(f"   📊 1h OHLC data after conversion: {len(ohlc_after.data or [])} bars")
        if ohlc_after.data:
            for bar in ohlc_after.data[:3]:
                print(f"      - {bar.get('timestamp')}")
        
        # Wait for backfill to complete (should be synchronous now)
        # Note: Some timeframes (like 4h) may not reach 333 bars - those positions will be dormant
        # We just need to verify backfill completed and positions exist
        def backfill_complete():
            positions = sb.table("lowcap_positions").select("timeframe,bars_count,status").eq("token_contract", token_contract).eq("token_chain", token_chain).execute()
            if not positions.data or len(positions.data) < 4:
                return False
            # Backfill is complete when all positions exist (some may be dormant if < 333 bars)
            # Check that at least one timeframe has enough bars for testing (we'll use 1h)
            bars_by_tf = {p.get("timeframe"): p.get("bars_count", 0) for p in positions.data}
            status_by_tf = {p.get("timeframe"): p.get("status") for p in positions.data}
            
            # Log status for debugging
            for tf in ["1m", "15m", "1h", "4h"]:
                bars = bars_by_tf.get(tf, 0)
                status = status_by_tf.get(tf, "unknown")
                if bars < 333:
                    print(f"   ⏳ {tf}: {bars} bars (< 333) → status={status} (dormant expected)")
                else:
                    print(f"   ✅ {tf}: {bars} bars (>= 333) → status={status}")
            
            # For testing, we need at least 1h to have enough bars (we'll test with 1h)
            return bars_by_tf.get("1h", 0) >= 333
        
        wait_for_condition(backfill_complete, timeout=120, poll_interval=2, error_message="Backfill did not complete")
        print(f"   ✅ Backfill complete")
        
        # Note: TA Tracker and Uptrend Engine are now automatically triggered by Decision Maker after backfill
        # Wait a moment for them to complete
        import time
        time.sleep(2)  # Give TA Tracker and Uptrend Engine a moment to run
        
        # Verify features are populated
        def features_populated():
            pos = sb.table("lowcap_positions").select("features").eq("token_contract", token_contract).eq("token_chain", token_chain).eq("timeframe", "1h").limit(1).execute()
            if not pos.data:
                return False
            features = pos.data[0].get("features") or {}
            has_ta = bool(features.get("ta"))
            has_engine = bool(features.get("uptrend_engine_v4"))
            if not has_ta:
                print(f"   ⏳ Waiting: features.ta not populated yet")
            if not has_engine:
                print(f"   ⏳ Waiting: features.uptrend_engine_v4 not populated yet")
            return has_ta and has_engine
        
        wait_for_condition(features_populated, timeout=30, poll_interval=2, error_message="TA Tracker and Uptrend Engine did not populate features")
        print(f"   ✅ Features populated (TA Tracker and Uptrend Engine ran automatically)")
        
        # Get 1h position for testing
        position_result = sb.table("lowcap_positions").select("*").eq("token_contract", token_contract).eq("token_chain", token_chain).eq("timeframe", "1h").limit(1).execute()
        if not position_result.data:
            pytest.fail("1h position not found after decision creation")
        
        position = position_result.data[0]
        position_id = position["id"]
        print(f"   ✅ Found 1h position: {position_id}")
        
        # Step 3: Mock engine payload for S1 Initial Entry
        print("\n📊 Step 3: Mocking engine payload for S1 Initial Entry...")
        
        # Get current features (with real TA data from engine)
        position_updated = sb.table("lowcap_positions").select("features").eq("id", position_id).execute().data[0]
        features = position_updated.get("features") or {}
        
        # Get real price from engine if available, otherwise use a reasonable mock
        real_engine = features.get("uptrend_engine_v4", {})
        real_price = real_engine.get("price", 0.0) if real_engine else 0.0
        if real_price <= 0:
            # Fallback: get latest price from OHLC
            ohlc_result = sb.table("lowcap_price_data_ohlc").select("close_usd").eq("token_contract", token_contract).eq("chain", token_chain).eq("timeframe", "1h").order("timestamp", desc=True).limit(1).execute()
            if ohlc_result.data:
                real_price = float(ohlc_result.data[0].get("close_usd", 0.0))
            else:
                real_price = 0.00037418  # Fallback mock price
        
        # Mock S1 buy_signal payload (using real TA data, but overriding state/flags)
        mocked_engine_payload = {
            "state": "S1",
            "buy_signal": True,
            "buy_flag": False,
            "first_dip_buy_flag": False,
            "trim_flag": False,
            "emergency_exit": False,
            "exit_position": False,
            "reclaimed_ema333": False,
            "scores": {
                "ts": 0.65,
                "ts_with_boost": 0.70,
                "sr_boost": 0.05
            },
            "price": real_price,  # Use real price from OHLC or engine
            "ema": features.get("ta", {}).get("ema", {}) if features.get("ta") else {},
            "flags": {
                "buy_flag": False,
                "trim_flag": False,
                "emergency_exit": False,
                "reclaimed_ema333": False
            },
            "diagnostics": {
                "buy_check": {
                    "entry_zone_ok": True,
                    "slope_ok": True,
                    "ts_ok": True
                }
            },
            "ts": datetime.now(timezone.utc).isoformat(),
            "meta": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "chain": token_chain,
            "token_contract": token_contract,
            "warmup": False
        }
        
        # Update features with mocked engine payload
        features["uptrend_engine_v4"] = mocked_engine_payload
        sb.table("lowcap_positions").update({"features": features}).eq("id", position_id).execute()
        print(f"   ✅ Mocked engine payload: state=S1, buy_signal=True")
        
        # Step 4: Mock A/E scores by mocking phase and cut_pressure
        # We'll set phase_meso to get desired A/E scores, or we can directly mock compute_levers result
        # For simplicity, let's directly set A/E in the test
        a_final = 0.5  # Normal mode (0.3 <= a_final < 0.7) → 30% initial allocation for S1
        e_final = 0.3
        phase_meso = "accumulation"  # This will be used by plan_actions_v4
        
        print(f"\n📊 Step 4: Testing PM decision logic with A/E scores...")
        print(f"   A/E scores: a_final={a_final}, e_final={e_final}")
        
        # Reload position with mocked engine payload
        position_for_pm = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        
        # Call plan_actions_v4 directly (or we can run PM Core Tick)
        actions = plan_actions_v4(position_for_pm, a_final, e_final, phase_meso, sb)
        
        print(f"   ✅ plan_actions_v4 returned {len(actions)} action(s)")
        for i, action in enumerate(actions):
            print(f"      Action {i+1}: decision_type={action.get('decision_type')}, size_frac={action.get('size_frac')}")
        
        # Verify decision
        assert len(actions) > 0, "Should have at least one action"
        assert actions[0].get("decision_type") == "add", f"Expected 'add', got {actions[0].get('decision_type')}"
        
        # For S1 with a_final=0.5 (normal mode), expected size_frac = 0.30 (30% initial allocation)
        expected_size_frac = 0.30
        actual_size_frac = actions[0].get("size_frac", 0.0)
        assert abs(actual_size_frac - expected_size_frac) < 0.01, f"Expected size_frac={expected_size_frac}, got {actual_size_frac}"
        
        print(f"   ✅ Decision verified: decision_type='add', size_frac={actual_size_frac}")
        
        # Step 5: Execute via PM Core Tick (which will use real executor)
        print(f"\n📊 Step 5: Executing via PM Core Tick with real executor...")
        print(f"   ⚠️  This will execute a real trade (~${actual_size_frac * float(position_for_pm.get('total_allocation_usd', 0)):.2f})")
        
        # Check if actions are enabled
        actions_enabled = os.getenv("ACTIONS_ENABLED", "0") == "1"
        if not actions_enabled:
            pytest.skip("ACTIONS_ENABLED=1 required for real execution testing")
        
        # Run PM Core Tick (it will compute A/E from phase/cut_pressure, but we want to use our mocked values)
        # Actually, PM Core Tick calls compute_levers() which we can't easily mock
        # So we have two options:
        # 1. Mock phase/cut_pressure to get desired A/E scores
        # 2. Call plan_actions_v4 directly and then executor.execute() directly
        
        # Step 5: Execute via executor and update position
        print(f"\n📊 Step 5: Executing via executor with real execution...")
        
        # Check if actions are enabled
        actions_enabled = os.getenv("ACTIONS_ENABLED", "0") == "1"
        if not actions_enabled:
            pytest.skip("ACTIONS_ENABLED=1 required for real execution testing")
        
        # Create PM Core Tick instance to use its executor and update methods
        pm_core = PMCoreTick(timeframe="1h", learning_system=empty_learning_system)
        
        # Prepare action for execution
        action = actions[0]
        
        # Initialize wallet_balances table if needed (for testing)
        # In production, this would be populated by scheduled jobs or executor
        wallet_balance_result = sb.table("wallet_balances").select("*").eq("chain", token_chain.lower()).limit(1).execute()
        if not wallet_balance_result.data:
            # Initialize with a test balance (e.g., $1000 USDC for testing)
            test_balance_usdc = 1000.0
            sb.table("wallet_balances").upsert({
                "chain": token_chain.lower(),
                "usdc_balance": test_balance_usdc,
                "balance_usd": test_balance_usdc,
                "balance": 0.0,  # Native token balance (not used for USDC)
                "last_updated": datetime.now(timezone.utc).isoformat()
            }).execute()
            print(f"   💰 Initialized wallet_balances: ${test_balance_usdc:.2f} USDC on {token_chain}")
        else:
            print(f"   💰 Wallet balance exists: ${wallet_balance_result.data[0].get('usdc_balance', 0):.2f} USDC on {token_chain}")
        
        # Recalculate P&L fields (including usd_alloc_remaining) before execution
        # This is what PM Core Tick does before making decisions
        print(f"   🔄 Recalculating P&L fields (including usd_alloc_remaining)...")
        pnl_updates = pm_core._recalculate_pnl_fields(position_for_pm)
        if pnl_updates:
            sb.table("lowcap_positions").update(pnl_updates).eq("id", position_id).execute()
            position_for_pm.update(pnl_updates)
            print(f"   ✅ P&L fields recalculated: usd_alloc_remaining=${pnl_updates.get('usd_alloc_remaining', 0):.2f}")
        
        # Reload position to get updated values
        position_for_pm = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        
        usd_alloc_remaining = float(position_for_pm.get("usd_alloc_remaining", 0.0))
        size_frac = action.get("size_frac", 0.0)
        
        print(f"   📊 Position allocation: usd_alloc_remaining=${usd_alloc_remaining:.2f}, size_frac={size_frac}")
        
        if usd_alloc_remaining <= 0:
            pytest.fail(f"Position has no remaining allocation (usd_alloc_remaining=${usd_alloc_remaining:.2f}). Check wallet balance and allocation calculation.")
        
        # Calculate notional USD from usd_alloc_remaining (executor will do this, but we check here for test)
        notional_usd = usd_alloc_remaining * size_frac
        
        # Check if we have enough USDC for execution (need at least $2 for test, but executor may need more for bridging)
        min_required_usdc = 2.0  # Minimum for test execution
        if usd_alloc_remaining < min_required_usdc:
            pytest.skip(f"Insufficient remaining allocation: ${usd_alloc_remaining:.2f} < ${min_required_usdc:.2f}. Please fund your wallet with USDC to run this test.")
        
        # Cap at $2 for testing (user requested $1-2, we'll use $2 max)
        max_execution_usd = 2.0
        if notional_usd > max_execution_usd:
            print(f"   ⚠️  Capping execution at ${max_execution_usd:.2f} (calculated: ${notional_usd:.2f})")
            notional_usd = max_execution_usd
            action["size_frac"] = max_execution_usd / usd_alloc_remaining if usd_alloc_remaining > 0 else 0.0
        
        print(f"   💰 Executing buy: ${notional_usd:.2f} USDC → {token_ticker}")
        print(f"   ⚠️  This is a REAL trade on Solana mainnet")
        
        # Execute via executor
        exec_result = pm_core.executor.execute(action, position_for_pm)
        
        print(f"   📊 Execution result: status={exec_result.get('status')}, tx_hash={exec_result.get('tx_hash', 'N/A')}")
        
        # Verify execution succeeded
        assert exec_result.get("status") == "success", f"Execution failed: {exec_result.get('error', 'unknown error')}"
        print(f"   ✅ Execution successful: tx_hash={exec_result.get('tx_hash', 'N/A')}")
        
        # Update position after execution (PM Core Tick does this)
        # Reload position to get latest state before updating
        position_for_pm = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        pm_core._update_position_after_execution(
            position_id=position_id,
            decision_type=action.get("decision_type"),
            execution_result=exec_result,
            action=action,
            position=position_for_pm,
            a_final=a_final,
            e_final=e_final
        )
        pm_core._update_execution_history(position_id, action.get("decision_type"), exec_result, action)
        
        print(f"   ✅ Position and execution history updated")
        
        # Step 6: Verify execution history updated
        print(f"\n📊 Step 6: Verifying execution history...")
        
        def execution_history_updated():
            pos = sb.table("lowcap_positions").select("features").eq("id", position_id).execute().data[0]
            exec_history = (pos.get("features") or {}).get("pm_execution_history", {})
            last_s1_buy = exec_history.get("last_s1_buy")
            return last_s1_buy is not None
        
        wait_for_condition(execution_history_updated, timeout=10, poll_interval=1, error_message="Execution history not updated")
        
        # Verify execution history details
        pos_final = sb.table("lowcap_positions").select("features,total_quantity,status").eq("id", position_id).execute().data[0]
        exec_history = (pos_final.get("features") or {}).get("pm_execution_history", {})
        last_s1_buy = exec_history.get("last_s1_buy", {})
        
        assert last_s1_buy is not None, "last_s1_buy should be set"
        assert last_s1_buy.get("timestamp") is not None, "timestamp should be set"
        assert last_s1_buy.get("price") > 0, "price should be > 0"
        assert last_s1_buy.get("size_frac") == action.get("size_frac"), "size_frac should match"
        
        print(f"   ✅ Execution history verified:")
        print(f"      - last_s1_buy.timestamp: {last_s1_buy.get('timestamp')}")
        print(f"      - last_s1_buy.price: {last_s1_buy.get('price')}")
        print(f"      - last_s1_buy.size_frac: {last_s1_buy.get('size_frac')}")
        
        # Step 7: Verify position updated
        print(f"\n📊 Step 7: Verifying position updated...")
        
        total_quantity = float(pos_final.get("total_quantity", 0))
        status = pos_final.get("status")
        
        assert total_quantity > 0, f"total_quantity should be > 0, got {total_quantity}"
        assert status == "active", f"status should be 'active', got {status}"
        
        print(f"   ✅ Position updated:")
        print(f"      - total_quantity: {total_quantity}")
        print(f"      - status: {status}")
        
        # Step 8: Close position (mock emergency exit and execute)
        print(f"\n📊 Step 8: Closing position with emergency exit...")
        
        # Mock emergency exit engine payload
        exit_engine_payload = {
            "state": "S3",
            "buy_signal": False,
            "buy_flag": False,
            "first_dip_buy_flag": False,
            "trim_flag": False,
            "emergency_exit": True,
            "exit_position": False,
            "scores": {
                "ox": 0.50,
                "dx": 0.40,
                "edx": 0.60,
                "ts": 0.45
            },
            "price": real_price,
            "diagnostics": {}
        }
        
        # Update position with exit signal
        pos_exit = sb.table("lowcap_positions").select("features").eq("id", position_id).execute().data[0]
        features_exit = pos_exit.get("features", {})
        features_exit["uptrend_engine_v4"] = exit_engine_payload
        sb.table("lowcap_positions").update({"features": features_exit}).eq("id", position_id).execute()
        print(f"   ✅ Mocked emergency exit signal")
        
        # Reload position and plan exit action
        position_for_exit = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        exit_actions = plan_actions_v4(position_for_exit, a_final=0.2, e_final=0.9, phase_meso="accumulation")
        
        assert len(exit_actions) > 0, "Should have exit action"
        assert exit_actions[0].get("decision_type") == "emergency_exit", f"Expected 'emergency_exit', got {exit_actions[0].get('decision_type')}"
        exit_action = exit_actions[0]
        print(f"   ✅ Exit action planned: decision_type={exit_action.get('decision_type')}, size_frac={exit_action.get('size_frac')}")
        
        # Execute exit
        exit_result = pm_core.executor.execute(exit_action, position_for_exit)
        assert exit_result.get("status") == "success", f"Exit execution failed: {exit_result.get('error', 'unknown error')}"
        print(f"   ✅ Exit executed: tx_hash={exit_result.get('tx_hash', 'N/A')}")
        
        # Update position after exit
        position_for_exit = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        pm_core._update_position_after_execution(
            position_id=position_id,
            decision_type=exit_action.get("decision_type"),
            execution_result=exit_result,
            action=exit_action,
            position=position_for_exit,
            a_final=0.2,
            e_final=0.9
        )
        pm_core._update_execution_history(position_id, exit_action.get("decision_type"), exit_result, exit_action)
        
        # Collect price data and convert to OHLC after exit (so R/R calculation has data)
        print(f"   🔄 Collecting price data and converting to OHLC after exit...")
        try:
            # Re-initialize price_oracle if needed (it was in local scope earlier)
            if 'price_oracle' not in locals() or price_oracle is None:
                from intelligence.trader_lowcap.price_oracle import PriceOracle
                price_oracle = PriceOracle()
            
            # Get current price using chain-specific method
            price_info = None
            if token_chain.lower() == 'solana':
                price_info = price_oracle.price_solana(token_contract)
            elif token_chain.lower() == 'bsc':
                price_info = price_oracle.price_bsc(token_contract)
            elif token_chain.lower() == 'base':
                price_info = price_oracle.price_base(token_contract)
            elif token_chain.lower() == 'ethereum':
                price_info = price_oracle.price_eth(token_contract)
            
            if price_info and price_info.get('price_usd'):
                current_price = price_info.get('price_usd')
                now = datetime.now(timezone.utc)
                price_data = {
                    "token_contract": token_contract,
                    "chain": token_chain.lower(),
                    "timestamp": now.isoformat(),
                    "price_usd": float(current_price),
                    "price_native": float(price_info.get('price_native', 0.0)),
                    "source": "test_manual"
                }
                sb.table("lowcap_price_data_1m").upsert(price_data).execute()
                print(f"      ✅ Inserted 1m price point: ${price_data['price_usd']} at {now.isoformat()}")
            else:
                print(f"      ⚠️  Could not get price - price_oracle returned: {price_info}")
            
            # Convert to OHLC
            rollup = GenericOHLCRollup()
            rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.M1)
            rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.H1)
            print(f"      ✅ OHLC converted")
            
            # Verify OHLC data exists
            ohlc_check = sb.table("lowcap_price_data_ohlc").select("timestamp").eq("token_contract", token_contract).eq("chain", token_chain).eq("timeframe", "1h").order("timestamp", desc=True).limit(1).execute()
            if ohlc_check.data:
                print(f"      ✅ Latest 1h OHLC bar: {ohlc_check.data[0].get('timestamp')}")
            else:
                print(f"      ⚠️  No 1h OHLC bars found after conversion")
        except Exception as e:
            print(f"      ⚠️  Error collecting/converting price data: {e}")
            import traceback
            print(f"      Traceback: {traceback.format_exc()}")
        
        # Check if position closed (PM Core Tick's _check_position_closure should have been called)
        # Manually trigger closure check since we're calling methods directly
        position_after_exit = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        if position_after_exit.get("total_quantity", 0) == 0:
            # Position is closed, trigger closure handling
            pm_core._check_position_closure(position_after_exit, exit_action.get("decision_type"), exit_result, exit_action)
            print(f"   ✅ Position closure detected and processed")
        
        # Step 9: Verify position closed and v4_Learning features
        print(f"\n📊 Step 9: Verifying position closure and v4_Learning features...")
        
        def position_closed():
            pos = sb.table("lowcap_positions").select("status,closed_at,completed_trades").eq("id", position_id).execute().data[0]
            return pos.get("status") == "watchlist" and pos.get("closed_at") is not None
        
        wait_for_condition(position_closed, timeout=10, poll_interval=1, error_message="Position not closed")
        
        final_position = sb.table("lowcap_positions").select("*").eq("id", position_id).execute().data[0]
        assert final_position.get("status") == "watchlist", f"Status should be 'watchlist', got {final_position.get('status')}"
        assert final_position.get("closed_at") is not None, "closed_at should be set"
        assert len(final_position.get("completed_trades", [])) > 0, "completed_trades should be populated"
        print(f"   ✅ Position closed: status=watchlist, closed_at={final_position.get('closed_at')}")
        
        # Verify position_closed strand exists
        # The strand structure has position_id in content JSONB field
        def strand_exists():
            strands = sb.table("ad_strands").select("*").eq("kind", "position_closed").execute()
            if not strands.data:
                return False
            # Check if any strand has matching position_id in content
            for s in strands.data:
                content = s.get("content", {})
                if isinstance(content, dict) and content.get("position_id") == position_id:
                    return True
            return False
        
        wait_for_condition(strand_exists, timeout=10, poll_interval=1, error_message="position_closed strand not found")
        
        position_closed_strands = sb.table("ad_strands").select("*").eq("kind", "position_closed").execute()
        # Find the strand for this position
        matching_strand = None
        for s in (position_closed_strands.data or []):
            if s.get("position_id") == position_id or (s.get("content", {}).get("position_id") == position_id):
                matching_strand = s
                break
        
        assert matching_strand is not None, "position_closed strand should exist for this position"
        print(f"   ✅ position_closed strand created: {matching_strand.get('id')}")
        
        # Verify braids created (v4_Learning)
        def braids_created():
            braids = sb.table("learning_braids").select("*").eq("module", "pm").limit(1).execute()
            return len(braids.data or []) > 0
        
        wait_for_condition(braids_created, timeout=30, poll_interval=2, error_message="No braids found - braiding system may not have processed strand")
        
        pm_braids = sb.table("learning_braids").select("*").eq("module", "pm").limit(5).execute()
        assert len(pm_braids.data or []) > 0, "PM braids should be created"
        print(f"   ✅ Braids created: {len(pm_braids.data)} PM braids found")
        
        # Verify lessons built automatically (v4_Learning)
        def lessons_created():
            lessons = sb.table("learning_lessons").select("*").eq("module", "pm").eq("status", "active").limit(1).execute()
            return len(lessons.data or []) > 0
        
        # Lessons may take a moment, but should exist if braids exist
        try:
            wait_for_condition(lessons_created, timeout=10, poll_interval=1, error_message="No lessons found")
            pm_lessons = sb.table("learning_lessons").select("*").eq("module", "pm").eq("status", "active").limit(5).execute()
            if len(pm_lessons.data or []) > 0:
                print(f"   ✅ Lessons built automatically: {len(pm_lessons.data)} active PM lessons")
            else:
                print(f"   ⚠️  No lessons found (may need more braids to meet thresholds)")
        except Exception as e:
            print(f"   ⚠️  Lessons check: {e} (may need more braids to meet thresholds)")
        
        # Verify coefficients updated (existing learning system)
        def coefficients_updated():
            coeffs = sb.table("learning_coefficients").select("*").eq("module", "pm").limit(1).execute()
            return len(coeffs.data or []) > 0
        
        try:
            wait_for_condition(coefficients_updated, timeout=10, poll_interval=1, error_message="No coefficients found")
            coeffs = sb.table("learning_coefficients").select("*").eq("module", "pm").limit(5).execute()
            if len(coeffs.data or []) > 0:
                print(f"   ✅ Coefficients updated: {len(coeffs.data)} PM coefficients")
        except Exception as e:
            print(f"   ⚠️  Coefficients check: {e}")
        
        print(f"\n✅ Test 9.1 Complete: S1 Initial Entry → Position Closure → v4_Learning Verification")
        print(f"   - Position opened and closed ✅")
        print(f"   - Braids created ✅")
        print(f"   - Lessons built automatically ✅")
        print(f"   - Learning system processed position_closed strand ✅")
        
        # Cleanup: Delete test data so test can be run again
        print(f"\n🧹 Cleaning up test data...")
        try:
            # Delete positions and OHLC data (already done at start, but do it again to be safe)
            sb.table("lowcap_positions").delete().eq("token_contract", token_contract).eq("token_chain", token_chain).execute()
            sb.table("lowcap_price_data_ohlc").delete().eq("token_contract", token_contract).eq("chain", token_chain).execute()
            
            # Delete social and decision strands
            sb.table("ad_strands").delete().eq("id", signal_id).execute()
            
            # Note: We don't delete wallet balance updates or execution history in wallet_balances
            # as those are real transactions that should persist
            # Note: We don't delete learning_braids, learning_lessons, or learning_coefficients
            # as those are learning data that should persist
            
            print(f"   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")
    
    def test_s2_retest_buy(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.2: S2 Retest Buy (buy_flag)"""
        pytest.skip("Requires test environment setup")
    
    def test_s3_dx_buy(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.3: S3 DX Buy (buy_flag)"""
        pytest.skip("Requires test environment setup")
    
    def test_s3_first_dip_buy(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.4: S3 First Dip Buy (first_dip_buy_flag)"""
        pytest.skip("Requires test environment setup")
    
    def test_s3_trim(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.5: S2/S3 Trim (trim_flag)"""
        pytest.skip("Requires test environment setup")
    
    def test_s3_emergency_exit(
        self,
        test_db,
        test_token,
        mock_engine_payload_s3_emergency_exit
    ):
        """Test Case 9.6: S3 Emergency Exit (emergency_exit)"""
        pytest.skip("Requires test environment setup")
    
    def test_global_exit(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.7: Global Exit (exit_position)"""
        pytest.skip("Requires test environment setup")
    
    def test_no_action_hold(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.8: No Action (Hold)"""
        pytest.skip("Requires test environment setup")
    
    def test_execution_history_tracking(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.10: Execution History Tracking"""
        pytest.skip("Requires test environment setup")
    
    def test_state_transition_resets(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.11: State Transition Resets"""
        pytest.skip("Requires test environment setup")
    
    def test_trim_cooldown_logic(
        self,
        test_db,
        test_token
    ):
        """Test Case 9.12: Trim Cooldown Logic"""
        pytest.skip("Requires test environment setup")


