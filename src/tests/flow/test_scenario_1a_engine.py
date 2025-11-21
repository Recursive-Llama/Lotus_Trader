"""
Flow Test: Scenario 1A - Uptrend Engine Testing (Real Data, No Execution)

Flow Testing Approach: Test engine computation with real OHLC data following actual system flow

Objective: Verify Uptrend Engine computes state/flags/scores correctly from real TA data

Flow Test Definition:
- Ingress: Social signal (like real system)
- Expected Path: 
  1. Social signal ingested
  2. Decision Maker processes signal and creates 4 positions (1m, 15m, 1h, 4h)
  3. Automatic backfill triggers for all 4 timeframes
  4. TA Tracker processes positions (populates features.ta)
  5. Uptrend Engine processes positions (computes features.uptrend_engine_v4)
  6. Engine payload validated for all timeframes
- Required Side-Effects: 
  - 4 positions created (one per timeframe)
  - All 4 timeframes backfilled (333+ bars each, target 666)
  - features.ta populated with EMA, ATR, RSI, slopes, etc.
  - features.uptrend_engine_v4 populated with state, flags, scores, diagnostics
- Timeout: 5 minutes
"""

import pytest
import sys
import os
import logging
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests.test_helpers import wait_for_condition
from intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker
from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import UptrendEngineV4
from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
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
class TestScenario1AEngine:
    """Test Scenario 1A: Uptrend Engine Testing - Following Real System Flow"""
    
    @pytest.mark.asyncio
    async def test_engine_computation_with_real_data(
        self,
        test_db,
        test_token,
        test_curator,
        test_signal_id,
        empty_learning_system
    ):
        """
        Verify engine computes state/flags/scores correctly from real TA data.
        
        This test follows the actual system flow:
        1. Ingest social signal
        2. Decision Maker creates 4 positions (triggers automatic backfill)
        3. Wait for backfill to complete for all 4 timeframes
        4. Run TA Tracker for all timeframes
        5. Run Uptrend Engine for all timeframes
        6. Validate engine payloads
        """
        print("\n📊 Step 1: Ingesting social signal...")
        sb = test_db.client
        
        token_contract = test_token["contract"]
        token_chain = test_token["chain"]
        token_ticker = test_token["ticker"]
        curator_id = test_curator.get("curator_id") or test_curator.get("id") or "0xdetweiler"
        
        # Clean up any existing positions and OHLC data for this token
        sb.table("lowcap_positions").delete().eq("token_contract", token_contract).eq("token_chain", token_chain).execute()
        sb.table("lowcap_price_data_ohlc").delete().eq("token_contract", token_contract).eq("chain", token_chain).execute()
        print(f"   ✅ Cleaned up existing positions and OHLC data for {token_ticker}")
        
        # Create social strand (same format as Scenario 1B)
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
                "curator": {
                    "id": curator_id,
                    "handle": test_curator.get("handle", curator_id),
                    "platform": "twitter",
                    "weight": 1.0
                },
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
                "venue": {
                    "dex": "raydium",
                    "chain": token_chain,
                    "liq_usd": 50000,
                    "vol24h_usd": 100000
                },
                "intent_analysis": {
                    "intent_analysis": {
                        "intent_type": "new_discovery",
                        "allocation_multiplier": 1.0,
                        "confidence": 0.8
                    }
                }
            },
            "content": {
                "curator_id": curator_id,
                "platform": "twitter",
                "handle": test_curator.get("handle", curator_id),
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
                "venue": {
                    "dex": "raydium",
                    "chain": token_chain,
                    "liq_usd": 50000,
                    "vol24h_usd": 100000
                },
                "message": {
                    "text": f"Check out {token_ticker}!",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "url": "https://twitter.com/test/status/123"
                },
                "curator_weight": 1.0,
                "context_slices": {}
            },
            "status": "active"
        }
        
        # Ensure curator exists with proper score
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
            print(f"   ✅ Created curator {curator_id} with score 0.7")
        else:
            sb.table("curators").update({
                "final_weight": 0.7,
                "win_rate": 0.7
            }).eq("curator_id", curator_id).execute()
            print(f"   ✅ Updated curator {curator_id} score to 0.7")
        
        # Insert social strand
        result = sb.table("ad_strands").insert(social_strand).execute()
        assert result.data, "Failed to create social_lowcap strand"
        created_strand = result.data[0]
        print(f"   ✅ Created social_lowcap strand: {created_strand['id']}")
        
        # Step 2: Decision Maker processes signal and creates positions
        print("\n📊 Step 2: Decision Maker processing signal and creating positions...")
        supabase_manager = SupabaseManager()
        config = {
            'book_id': 'social',
            'min_curator_score': 0.6,
            'max_exposure_pct': 100.0,
            'max_positions': 69,
            'trading': {
                'min_curator_score': 0.6,
                'max_exposure_pct': 100.0,
                'max_positions': 69
            },
            'allocation_config': {
                'social_curators': {
                    'excellent_score': 0.8,
                    'excellent_allocation': 15.0,
                    'good_score': 0.6,
                    'good_allocation': 6.0,
                    'acceptable_allocation': 4.0
                },
                'gem_bot': {
                    'conservative_allocation': 6.0,
                    'balanced_allocation': 4.0,
                    'risky_allocation': 2.0
                },
                'test_mode': {
                    'social_curators_multiplier': 0.1,
                    'gem_bot_multiplier': 0.2
                }
            },
            'min_volume_requirements': {
                'solana': 100000,
                'ethereum': 25000,
                'base': 25000
            }
        }
        decision_maker = DecisionMakerLowcapSimple(
            supabase_manager=supabase_manager,
            config=config,
            learning_system=empty_learning_system
        )
        
        print(f"   🔄 Calling decision_maker.make_decision()...")
        decision = await decision_maker.make_decision(social_strand)
        if not decision:
            pytest.skip("Decision Maker rejected signal - cannot continue test")
        
        print(f"   ✅ Decision created, positions should be created with automatic backfill")
        print(f"   📝 Note: Backfill is now synchronous, so it should complete before make_decision() returns")
        
        # Immediately check positions after decision
        print("\n   🔍 Checking positions immediately after decision...")
        initial_positions = (
            sb.table("lowcap_positions")
            .select("id,timeframe,bars_count,status,created_at")
            .eq("token_contract", token_contract)
            .eq("token_chain", token_chain)
            .execute()
        )
        if initial_positions.data:
            print(f"   📊 Found {len(initial_positions.data)} positions:")
            for p in initial_positions.data:
                print(f"      - {p.get('timeframe')}: id={p.get('id')}, bars={p.get('bars_count', 0)}, status={p.get('status')}")
        else:
            print(f"   ⚠️ No positions found yet - this might indicate an issue")
        
        # Step 3: Wait for automatic backfill to complete for all 4 timeframes
        print("\n📊 Step 3: Checking backfill status (all 4 timeframes)...")
        print("   📝 Since backfill is now synchronous, it should already be complete")
        
        def backfill_complete():
            positions = (
                sb.table("lowcap_positions")
                .select("timeframe,bars_count,status,created_at")
                .eq("token_contract", token_contract)
                .eq("token_chain", token_chain)
                .execute()
            )
            if not positions.data:
                print(f"      ⏳ No positions found yet...")
                return False
            if len(positions.data) < 4:
                print(f"      ⏳ Waiting for positions... ({len(positions.data)}/4 found)")
                for p in positions.data:
                    print(f"         - {p.get('timeframe')}: bars={p.get('bars_count', 0)}, status={p.get('status')}")
                return False
            
            # Check if all timeframes have bars (backfill started)
            bars_by_tf = {p.get("timeframe"): p.get("bars_count", 0) for p in positions.data}
            status_by_tf = {p.get("timeframe"): p.get("status") for p in positions.data}
            all_have_bars = all(bars > 0 for bars in bars_by_tf.values())
            
            if not all_have_bars:
                print(f"      ⏳ Waiting for backfill... Current status:")
                for tf in ['1m', '15m', '1h', '4h']:
                    bars = bars_by_tf.get(tf, 0)
                    status = status_by_tf.get(tf, 'unknown')
                    print(f"         - {tf}: {bars} bars, status={status}")
            else:
                print(f"      ✅ All timeframes have bars:")
                for tf in ['1m', '15m', '1h', '4h']:
                    bars = bars_by_tf.get(tf, 0)
                    status = status_by_tf.get(tf, 'unknown')
                    print(f"         - {tf}: {bars} bars, status={status}")
            
            return all_have_bars
        
        # Since backfill is now synchronous, it should complete quickly
        # But we'll still wait a bit in case of database propagation delays
        print("   ⏳ Waiting for backfill to complete (checking every 2 seconds)...")
        wait_for_condition(
            backfill_complete,
            timeout=120,  # Reduced timeout since backfill is synchronous (2 minutes should be plenty)
            poll_interval=2,  # Check more frequently
            error_message="Automatic backfill did not complete for all timeframes within timeout"
        )
        
        # Verify backfill results
        positions = (
            sb.table("lowcap_positions")
            .select("id,timeframe,bars_count,status")
            .eq("token_contract", token_contract)
            .eq("token_chain", token_chain)
            .order("timeframe")
            .execute()
        )
        
        position_ids = {}
        for pos in positions.data:
            tf = pos.get("timeframe")
            pos_id = pos.get("id")
            bars = pos.get("bars_count", 0)
            status = pos.get("status")
            position_ids[tf] = pos_id
            print(f"   {tf}: {bars} bars, status={status}, id={pos_id}")
            # Allow for slight variation due to deduplication (minimum 333 bars, target 666)
            assert bars >= 333, f"{tf} should have at least 333 bars (target 666), got {bars}"
        
        assert len(position_ids) == 4, f"Should have 4 positions, got {len(position_ids)}"
        print(f"   ✅ Automatic backfill completed for all 4 timeframes")
        
        # Step 4: Run TA Tracker for all timeframes
        print("\n📊 Step 4: Running TA Tracker for all timeframes...")
        for tf in ['1m', '15m', '1h', '4h']:
            ta_tracker = TATracker(timeframe=tf)
            ta_updated = ta_tracker.run()
            print(f"   {tf}: Updated {ta_updated} positions")
        
        # Verify TA data populated for all timeframes
        for tf in ['1m', '15m', '1h', '4h']:
            pos_id = position_ids[tf]
            def has_ta_data():
                pos = (
                    sb.table("lowcap_positions")
                    .select("features")
                    .eq("id", pos_id)
                    .execute()
                )
                if not pos.data:
                    return False
                features = pos.data[0].get("features") or {}
                ta = features.get("ta")
                if not ta:
                    return False
                ema = ta.get("ema", {})
                return bool(ema.get(f"ema60_{tf}") or ema.get("ema60_1h") or ema.get("ema60"))
            
            wait_for_condition(
                has_ta_data,
                timeout=30,
                poll_interval=2,
                error_message=f"TA Tracker did not populate features.ta for {tf}"
            )
            print(f"   ✅ {tf}: TA data populated")
        
        # Step 5: Run Uptrend Engine for all timeframes
        print("\n📊 Step 5: Running Uptrend Engine for all timeframes...")
        for tf in ['1m', '15m', '1h', '4h']:
            uptrend_engine = UptrendEngineV4(timeframe=tf)
            engine_updated = uptrend_engine.run()
            print(f"   {tf}: Updated {engine_updated} positions")
        
        # Step 6: Validate engine payloads for all timeframes
        print("\n📊 Step 6: Validating engine payloads for all timeframes...")
        for tf in ['1m', '15m', '1h', '4h']:
            pos_id = position_ids[tf]
            pos = (
                sb.table("lowcap_positions")
                .select("features")
                .eq("id", pos_id)
                .execute()
            )
            features = pos.data[0].get("features") or {}
            engine = features.get("uptrend_engine_v4", {})
            
            # Validate state
            state = engine.get("state", "")
            valid_states = ["S0", "S1", "S2", "S3", "S4"]
            assert state in valid_states, f"{tf}: state should be one of {valid_states}, got {state}"
            
            # Validate flags
            flags = engine.get("flags", {})
            assert isinstance(flags, dict), f"{tf}: flags should be a dict"
            
            # Validate scores (may be None for some states)
            scores = engine.get("scores")
            if scores is not None:
                assert isinstance(scores, dict), f"{tf}: scores should be a dict or None"
            
            # Validate price
            price = engine.get("price", 0.0)
            assert price > 0, f"{tf}: price should be > 0, got {price}"
            
            print(f"   ✅ {tf}: state={state}, price=${price:.8f}, scores={scores is not None}")
        
        print("\n✅ Scenario 1A Complete: Uptrend Engine computed for all 4 timeframes following real system flow")
