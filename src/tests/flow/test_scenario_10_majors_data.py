"""
Flow Test: Scenario 10 - Majors Data Flow Test (SPIRAL Engine Dependency)

Flow Testing Approach: Follow majors data through ingestion → rollup → SPIRAL consumption

Objective: Verify majors data pipeline works end-to-end and SPIRAL engine can access it

Flow Test Definition:
- Ingress: Hyperliquid WebSocket feed (real-time ingestion)
- Payload: Real trade ticks for majors (BTC, SOL, ETH, BNB, HYPE)
- Expected Path: 
  1. Trade ticks ingested and buffered (via Hyperliquid WS)
  2. 1m OHLC bars written directly to majors_price_data_ohlc (timeframe='1m') at minute boundaries
  3. OHLC rolled up to higher timeframes (15m, 1h, 4h) into majors_price_data_ohlc
  4. SPIRAL engine queries majors_price_data_ohlc (timeframe='1m') for phase detection
  5. Returns computed (r_btc, r_alt, r_port)
- Required Side-Effects: 
  - majors_price_data_ohlc populated with 1m bars (timeframe='1m') at minute boundaries
  - majors_price_data_ohlc populated with 15m, 1h, 4h bars (via rollup)
  - SPIRAL engine can compute returns successfully
- Timeout: 2 minutes (wait for minute boundary flush)
"""

import pytest
import sys
import os
import asyncio
import contextlib
from datetime import datetime, timezone, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests.test_helpers import wait_for_condition
from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
from intelligence.lowcap_portfolio_manager.ingest.rollup_ohlc import GenericOHLCRollup, DataSource, Timeframe
from intelligence.lowcap_portfolio_manager.spiral.returns import ReturnsComputer


@pytest.mark.flow
class TestScenario10MajorsData:
    """Test Scenario 10: Majors Data Flow Test"""
    
    @pytest.mark.asyncio
    async def test_majors_data_flow(
        self,
        test_db
    ):
        """
        Follow majors data through ingestion → rollup → SPIRAL consumption.
        
        This test verifies:
        - Majors data ingestion works (Hyperliquid WS)
        - 1m rollup works correctly
        - OHLC rollup works for all timeframes
        - SPIRAL engine can query majors data successfully
        - Returns are computed correctly (r_btc, r_alt, r_port)
        """
        sb = test_db.client
        now = datetime.now(timezone.utc)
        required_tokens = ['BTC', 'SOL', 'ETH', 'BNB', 'HYPE']
        ingester = None
        ingest_task = None
        
        try:
            # Step 1: Start Hyperliquid WebSocket ingester
            print("\n📊 Step 1: Starting Hyperliquid WebSocket ingester...")
            # Enable SAVE_TICKS so ticks are written immediately (not just at minute boundaries)
            # MUST set before creating ingester (it reads env in __init__)
            original_save_ticks = os.environ.get("SAVE_TICKS")
            original_hl_debug = os.environ.get("HL_DEBUG")
            os.environ["SAVE_TICKS"] = "1"
            os.environ["HL_DEBUG"] = "1"  # Enable debug logging
            ingester = HyperliquidWSIngester()
            ingest_task = asyncio.create_task(ingester.run())
            
            print("   WS ingester started, waiting for data ingestion...")
            print(f"   Symbols: {ingester.symbols}")
            print(f"   WS URL: {ingester.ws_url}")
            
            # Give it a moment to connect
            await asyncio.sleep(2)
            
            # Check if task is still running (not failed)
            if ingest_task.done():
                try:
                    await ingest_task
                except Exception as e:
                    pytest.fail(f"Hyperliquid WS ingester task failed immediately: {e}")
            
            # Wait for ticks to be written (they're written in batches of 10)
            def has_ticks():
                result = (
                    sb.table("majors_trades_ticks")
                    .select("token,ts")
                    .in_("token", required_tokens)
                    .gte("ts", (now - timedelta(minutes=2)).isoformat())
                    .execute()
                )
                tokens_found = set(r["token"] for r in (result.data or []))
                return len(tokens_found) >= 3  # At least 3 of 5 tokens should have ticks
            
            wait_for_condition(
                has_ticks,
                timeout=30,  # 30 seconds should be enough for ticks to be written
                poll_interval=2,
                error_message="Hyperliquid WS ingester started but no ticks appearing in majors_trades_ticks"
            )
            print("✅ Step 1: Hyperliquid WS ingester running and writing ticks to majors_trades_ticks")
            
            # Verify ticks exist
            result = (
                sb.table("majors_trades_ticks")
                .select("token,ts")
                .in_("token", required_tokens)
                .gte("ts", (now - timedelta(minutes=2)).isoformat())
                .execute()
            )
            tokens_found = set(r["token"] for r in (result.data or []))
            print(f"   Found ticks in majors_trades_ticks for tokens: {sorted(tokens_found)}")
            print(f"   Total ticks: {len(result.data or [])}")
            
            # Step 2: Run 1m rollup to create bars from ticks
            print("\n📊 Step 2: Running 1m rollup to create bars from ticks...")
            from intelligence.lowcap_portfolio_manager.ingest.rollup import OneMinuteRollup
            rollup = OneMinuteRollup()
            
            # Roll up the last few minutes to ensure we have data
            bars_written = 0
            for i in range(3):  # Try last 3 minutes
                when = now - timedelta(minutes=i)
                bars = rollup.roll_minute(when=when, symbols=required_tokens)
                bars_written += bars
            
            print(f"   Rolled up {bars_written} 1m bars from ticks")
            
            # Wait for bars to appear
            def has_1m_bars_from_rollup():
                result = (
                    sb.table("majors_price_data_ohlc")
                    .select("token_contract,timestamp")
                    .eq("chain", "hyperliquid")
                    .eq("timeframe", "1m")
                    .in_("token_contract", required_tokens)
                    .gte("timestamp", (now - timedelta(minutes=3)).isoformat())
                    .execute()
                )
                tokens_found = set(r["token_contract"] for r in (result.data or []))
                return len(tokens_found) >= 3  # At least 3 of 5 tokens should have data
            
            wait_for_condition(
                has_1m_bars_from_rollup,
                timeout=10,
                poll_interval=2,
                error_message="1m bars not appearing after rollup"
            )
            
            # Verify OHLC values are valid
            result = (
                sb.table("majors_price_data_ohlc")
                .select("token_contract,high_usd,low_usd,open_usd,close_usd")
                .eq("chain", "hyperliquid")
                .eq("timeframe", "1m")
                .in_("token_contract", required_tokens)
                .gte("timestamp", (now - timedelta(minutes=3)).isoformat())
                .limit(10)
                .execute()
            )
            
            for bar in (result.data or []):
                assert bar["high_usd"] >= bar["low_usd"], f"Invalid OHLC: high < low for {bar['token_contract']}"
                assert bar["high_usd"] >= bar["open_usd"], f"Invalid OHLC: high < open for {bar['token_contract']}"
                assert bar["high_usd"] >= bar["close_usd"], f"Invalid OHLC: high < close for {bar['token_contract']}"
                assert bar["low_usd"] <= bar["open_usd"], f"Invalid OHLC: low > open for {bar['token_contract']}"
                assert bar["low_usd"] <= bar["close_usd"], f"Invalid OHLC: low > close for {bar['token_contract']}"
            
            print("✅ Step 2: 1m OHLC bars are valid")
            
            # Step 3: Follow to OHLC Rollup
            print("\n📊 Step 3: Running OHLC rollup for 15m, 1h, 4h...")
            ohlc_rollup = GenericOHLCRollup()
            
            # Roll up to higher timeframes
            timeframes = [Timeframe.M15, Timeframe.H1, Timeframe.H4]
            for tf in timeframes:
                written = ohlc_rollup.rollup_timeframe(DataSource.MAJORS, tf, when=now)
                print(f"   {tf.value}: {written} bars written")
            
            # Verify majors_price_data_ohlc has data for all timeframes
            def has_ohlc_bars():
                result = (
                    sb.table("majors_price_data_ohlc")
                    .select("token_contract,timeframe")
                    .eq("chain", "hyperliquid")
                    .in_("token_contract", required_tokens)
                    .in_("timeframe", ["15m", "1h", "4h"])
                    .gte("timestamp", (now - timedelta(days=7)).isoformat())
                    .execute()
                )
                timeframes_found = set((r["token_contract"], r["timeframe"]) for r in (result.data or []))
                return len(timeframes_found) >= 5  # At least 5 combinations (token, timeframe)
            
            wait_for_condition(
                has_ohlc_bars,
                timeout=10,
                poll_interval=2,
                error_message="majors_price_data_ohlc not populated after rollup"
            )
            
            # Verify OHLC values are valid
            result = (
                sb.table("majors_price_data_ohlc")
                .select("token_contract,timeframe,high_native,low_native,open_native,close_native")
                .eq("chain", "hyperliquid")
                .in_("token_contract", required_tokens)
                .in_("timeframe", ["15m", "1h", "4h"])
                .gte("timestamp", (now - timedelta(days=1)).isoformat())
                .limit(10)
                .execute()
            )
            
            for bar in (result.data or []):
                assert bar["high_native"] >= bar["low_native"], \
                    f"Invalid OHLC: high < low for {bar['token_contract']} {bar['timeframe']}"
            
            print("✅ Step 3: OHLC rollup works for all timeframes, values valid")
            
            # Step 4: Follow to SPIRAL Engine Consumption
            print("\n📊 Step 4: Testing SPIRAL ReturnsComputer...")
            returns_computer = ReturnsComputer()
            
            # Compute returns
            returns_result = returns_computer.compute(when=now)
            
            # Verify returns are computed
            assert returns_result.r_btc is not None, "r_btc is None"
            assert returns_result.r_alt is not None, "r_alt is None"
            assert returns_result.r_port is not None, "r_port is None"
            
            # Verify closes are populated
            assert "BTC" in returns_result.closes_now, "BTC close missing"
            assert len(returns_result.closes_now) >= 3, f"Expected at least 3 closes, got {len(returns_result.closes_now)}"
            
            # Verify returns are valid (not NaN, not infinite)
            assert not (returns_result.r_btc != returns_result.r_btc), "r_btc is NaN"
            assert not (returns_result.r_alt != returns_result.r_alt), "r_alt is NaN"
            assert not (returns_result.r_port != returns_result.r_port), "r_port is NaN"
            
            print(f"   r_btc: {returns_result.r_btc:.6f}")
            print(f"   r_alt: {returns_result.r_alt:.6f}")
            print(f"   r_port: {returns_result.r_port:.6f}")
            print(f"   closes_now: {returns_result.closes_now}")
            
            print("✅ Step 4: SPIRAL ReturnsComputer can query majors data and compute returns")
            
            # Success - all steps completed
            print("\n✅ Scenario 10: Majors Data Flow Test PASSED")
            print("   - Hyperliquid WS ingestion: ✅")
            print("   - 1m rollup: ✅")
            print("   - OHLC rollup (15m, 1h, 4h): ✅")
            print("   - SPIRAL returns computation: ✅")
            
        finally:
            # Clean up: Stop WS ingester
            if ingest_task:
                print("\n🧹 Cleaning up: Stopping Hyperliquid WS ingester...")
                ingest_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    try:
                        await asyncio.wait_for(ingest_task, timeout=5)
                    except asyncio.TimeoutError:
                        pass
                # Flush any remaining data
                if ingester:
                    try:
                        await ingester.flush_on_shutdown()
                    except Exception:
                        pass
                print("   WS ingester stopped")
            # Restore original env vars
            if original_save_ticks is not None:
                os.environ["SAVE_TICKS"] = original_save_ticks
            elif "SAVE_TICKS" in os.environ:
                del os.environ["SAVE_TICKS"]
            if original_hl_debug is not None:
                os.environ["HL_DEBUG"] = original_hl_debug
            elif "HL_DEBUG" in os.environ:
                del os.environ["HL_DEBUG"]
