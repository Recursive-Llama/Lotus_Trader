"""
PM Action Harness
=================

End-to-end harness that exercises the PM action loop by:
1. Ensuring a test position exists (reuses the social→decision harness if needed).
2. Forcing controlled uptrend-engine states (S0→S1→S3→S0) and running `pm_core_tick`.
3. Validating that PM emits stage-transition / action strands and updates the position.

Usage:
    PYTHONPATH=src python tests/flow/pm_action_harness.py --log-level INFO
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import time

from dotenv import load_dotenv

from utils.supabase_manager import SupabaseManager
from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
try:
    from tests.flow.pm_learning_flow_harness import PMLearningFlowHarness
except ModuleNotFoundError:  # pragma: no cover
    from pm_learning_flow_harness import PMLearningFlowHarness


LOGGER = logging.getLogger("pm_action_harness")


class HarnessMockExecutor:
    """
    Lightweight executor stub for harness runs.
    Returns deterministic fills so pm_core_tick can update quantities
    without needing real wallets/RPC access.
    """

    def __init__(self, sb_client, fail_mode: Optional[str] = None, partial_fill: bool = False) -> None:
        self.sb = sb_client
        self.logger = logging.getLogger("HarnessMockExecutor")
        self.fail_mode = fail_mode  # "entry", "exit", or None
        self.partial_fill = partial_fill  # If True, return partial fill

    def execute(self, decision: Dict[str, Any], position: Dict[str, Any]) -> Dict[str, Any]:
        decision_type = (decision.get("decision_type") or "").lower()
        if decision_type in ("", "hold"):
            return {"status": "error", "error": "No-op decision"}

        price = self._resolve_price(position)
        if price <= 0:
            return {"status": "error", "error": "mock price unavailable"}

        size_frac = max(0.0, float(decision.get("size_frac") or 0.0))
        total_qty = float(position.get("total_quantity") or 0.0)
        alloc_usd = float(
            position.get("usd_alloc_remaining")
            or position.get("total_allocation_usd")
            or 0.0
        )

        tx_hash = f"mock-{decision_type}-{int(time.time())}"

        if decision_type in ("entry", "add", "trend_add"):
            # Check for failure mode
            if self.fail_mode == "entry":
                return {"status": "error", "error": "Mock executor failure for entry"}
            
            if alloc_usd <= 0:
                # Fallback to a nominal notional so quantities advance.
                alloc_usd = 100.0
            notional_usd = max(0.0, alloc_usd * size_frac)
            tokens_bought = notional_usd / price if price > 0 else 0.0
            
            # Handle partial fill
            if self.partial_fill:
                tokens_bought = tokens_bought * 0.5  # 50% fill
                notional_usd = tokens_bought * price
            
            return {
                "status": "success",
                "tx_hash": tx_hash,
                "tokens_bought": tokens_bought,
                "tokens_sold": 0.0,
                "price": price,
                "price_native": price,
                "notional_usd": notional_usd,
                "actual_usd": 0.0,
                "slippage": 0.0,
            }

        if decision_type in ("trim", "emergency_exit"):
            # Check for failure mode
            if self.fail_mode == "exit":
                return {"status": "error", "error": "Mock executor failure for exit"}
            
            tokens_sold = total_qty if decision_type == "emergency_exit" else total_qty * size_frac
            tokens_sold = max(0.0, tokens_sold)
            actual_usd = tokens_sold * price
            return {
                "status": "success",
                "tx_hash": tx_hash,
                "tokens_bought": 0.0,
                "tokens_sold": tokens_sold,
                "price": price,
                "price_native": price,
                "notional_usd": 0.0,
                "actual_usd": actual_usd,
                "slippage": 0.0,
            }

        return {"status": "error", "error": f"Unsupported decision {decision_type}"}

    def _resolve_price(self, position: Dict[str, Any]) -> float:
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        price = float(uptrend.get("price") or 0.0)
        if price > 0:
            return price

        try:
            result = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("close_usd")
                .eq("token_contract", position.get("token_contract"))
                .eq("chain", position.get("token_chain"))
                .eq("timeframe", position.get("timeframe", "1h"))
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                price = float(result.data[0].get("close_usd") or 0.0)
        except Exception as exc:
            self.logger.debug("mock executor price lookup failed: %s", exc)

        return price


class PMActionHarness:
    TEST_CONTRACT = "BkpaxHhE6snExazrPkVAjxDyZa8Nq3oDEzm5GQm2pump"
    TEST_CHAIN = "solana"
    TEST_TIMEFRAME = "1h"

    def __init__(self) -> None:
        load_dotenv()
        # Enable actions for testing (use small amounts to test real execution flow)
        import os
        os.environ["ACTIONS_ENABLED"] = "1"
        os.environ["PM_USE_V4"] = "1"
        self.supabase_manager = SupabaseManager()
        self.sb = self.supabase_manager.client
        self.position: Dict[str, Any] | None = None
        self.position_id: int | None = None
        self.start_ts: datetime = datetime.now(timezone.utc)

    def run(self) -> None:
        logging.basicConfig(level=LOGGER.level or logging.INFO)
        self._ensure_position()
        self.start_ts = datetime.now(timezone.utc)
        self._sanitize_execution_history()

        scenarios = [
            {
                "name": "S1 entry",
                "uptrend": self._make_uptrend_state(
                    "S1",
                    buy_signal=True,
                    buy_flag=False,
                    trim_flag=False,
                    emergency_exit=False,
                ),
                "expected_status": "active",  # Should enter, stay active
                "reset_to_watchlist": True,   # Force fresh entry slot
            },
            {
                "name": "S3 retest buy",
                "uptrend": self._make_uptrend_state(
                    "S3",
                    buy_signal=False,
                    buy_flag=True,
                    trim_flag=False,
                    emergency_exit=False,
                ),
                "expected_status": "active",  # Should add, stay active
            },
            {
                "name": "S3 emergency_exit (price < EMA333)",
                "uptrend": self._make_uptrend_state(
                    "S3",
                    buy_signal=False,
                    buy_flag=False,
                    trim_flag=False,
                    emergency_exit=True,  # Price < EMA333
                ),
                "expected_status": "active",  # Should sell 100%, but state still S3 (not S0 yet)
            },
            {
                "name": "S3 → S0 transition (all EMAs below 333)",
                "uptrend": self._make_uptrend_state(
                    "S0",
                    buy_signal=False,
                    buy_flag=False,
                    trim_flag=False,
                    emergency_exit=False,
                    exit_position=True,  # All EMAs below EMA333
                ),
                "expected_status": "watchlist",  # Should close trade
            },
            {
                "name": "S1 → S0 transition (fast_band_at_bottom)",
                "uptrend": self._make_uptrend_state(
                    "S0",
                    buy_signal=False,
                    buy_flag=False,
                    trim_flag=False,
                    emergency_exit=False,
                    exit_position=True,  # fast_band_at_bottom
                ),
                "expected_status": "watchlist",  # Should close trade
            },
            {
                "name": "S0 with no trade (watchlist)",
                "uptrend": self._make_uptrend_state(
                    "S0",
                    buy_signal=False,
                    buy_flag=False,
                    trim_flag=False,
                    emergency_exit=False,
                ),
                "expected_status": "watchlist",  # Already closed, should stay closed
                "ensure_no_trade": True,  # Clear trade_id before test
            },
        ]
        
        # Run edge case tests
        self._run_edge_case_tests()

        for scenario in scenarios:
            LOGGER.info("=== %s ===", scenario["name"])
            
            # Set up position state for this scenario
            if scenario.get("ensure_no_trade"):
                # Clear trade_id and set to watchlist for scenarios that shouldn't have a trade
                self._clear_trade_id()
            elif scenario.get("reset_to_watchlist"):
                # Force reset when scenario explicitly needs a fresh slot
                self._ensure_watchlist_state()
            
            self._apply_uptrend_state(scenario["uptrend"])
            LOGGER.info("Running pm_core_tick...")
            try:
                pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
                pm_tick.executor = HarnessMockExecutor(pm_tick.sb)
                strands_written = pm_tick.run()
                LOGGER.info("pm_core_tick completed, wrote %d strands", strands_written)
            except Exception as e:
                LOGGER.error("pm_core_tick failed: %s", e, exc_info=True)
                raise
            self._refresh_position()
            self._print_step_summary(scenario["name"])
            
            # Validate expected status
            expected_status = scenario.get("expected_status")
            if expected_status:
                actual_status = self.position.get("status") if self.position else None
                if actual_status == expected_status:
                    LOGGER.info("✓ Status check PASSED: %s", expected_status)
                else:
                    LOGGER.error(
                        "✗ Status check FAILED: expected=%s, actual=%s",
                        expected_status,
                        actual_status,
                    )

    def _ensure_position(self) -> None:
        self._refresh_position()
        if self.position:
            LOGGER.info(
                "Found existing position id=%s status=%s",
                self.position_id,
                self.position.get("status"),
            )
            return

        LOGGER.info("No %s position found – running social harness to create one", self.TEST_TIMEFRAME)
        harness = PMLearningFlowHarness()
        asyncio.run(harness.run(run_learning_jobs=False))
        self._refresh_position()
        if not self.position:
            raise RuntimeError("Failed to create test position via learning harness")
        LOGGER.info("Created position id=%s via social harness", self.position_id)

    def _refresh_position(self) -> None:
        resp = (
            self.sb.table("lowcap_positions")
            .select("*")
            .eq("token_contract", self.TEST_CONTRACT)
            .eq("token_chain", self.TEST_CHAIN)
            .eq("timeframe", self.TEST_TIMEFRAME)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        self.position = rows[0] if rows else None
        self.position_id = self.position.get("id") if self.position else None

    def _apply_uptrend_state(self, uptrend_overrides: Dict[str, Any]) -> None:
        if not self.position_id:
            raise RuntimeError("Test position missing")
        features = deepcopy(self.position.get("features") or {})
        features["uptrend_engine_v4"] = uptrend_overrides
        features["ta"] = self._build_ta_features()
        features["geometry"] = {
            "sr_break": "bull",
            "sr_conf": 0.8,
            "diag_break": "neutral",
            "diag_conf": 0.4,
            "at_support": True,
        }
        exec_history = features.get("pm_execution_history")
        if not isinstance(exec_history, dict):
            exec_history = {}
        exec_history = {k: v for k, v in exec_history.items() if v is not None}
        features["pm_execution_history"] = exec_history
        features.setdefault("intent_signals", {"confidence": 0.8, "time_efficiency": 0.7})
        features.setdefault("position_age_hours", 0.5)
        features.setdefault("market_cap_usd", 1_500_000)

        self.sb.table("lowcap_positions").update({"features": features}).eq("id", self.position_id).execute()
        LOGGER.info("Updated features for position %s (state=%s)", self.position_id, uptrend_overrides.get("state"))
        self._refresh_position()

    def _build_ta_features(self) -> Dict[str, Any]:
        return {
            "ema_slopes": {
                "ema60_slope_1h": 0.012,
                "ema144_slope_1h": 0.006,
                "ema250_slope_1h": 0.003,
                "ema333_slope_1h": 0.002,
            },
            "atr": {
                "atr_1h": 0.00015,
                "atr_norm_1h": 0.1,
            },
        }

    def _clear_trade_id(self) -> None:
        """Clear current_trade_id to simulate watchlist position."""
        if not self.position_id:
            return
        features = deepcopy(self.position.get("features") or {})
        # Clear trade_id and set status to watchlist
        self.sb.table("lowcap_positions").update({
            "current_trade_id": None,
            "status": "watchlist",
        }).eq("id", self.position_id).execute()
        self._refresh_position()
        LOGGER.info("Cleared trade_id for position %s", self.position_id)
    
    def _ensure_watchlist_state(self) -> None:
        """Ensure position is in watchlist state with no trade_id (ready for new entry)."""
        if not self.position_id:
            return
        current_status = self.position.get("status")
        current_trade_id = self.position.get("current_trade_id")
        
        if current_status != "watchlist" or current_trade_id:
            LOGGER.info("Resetting position %s to watchlist state (was: status=%s, trade_id=%s)", 
                       self.position_id, current_status, current_trade_id)
            self.sb.table("lowcap_positions").update({
                "current_trade_id": None,
                "status": "watchlist",
            }).eq("id", self.position_id).execute()
            self._refresh_position()

    def _make_uptrend_state(
        self,
        state: str,
        *,
        buy_signal: bool,
        buy_flag: bool,
        trim_flag: bool,
        emergency_exit: bool,
        exit_position: bool = False,
    ) -> Dict[str, Any]:
        ema_values = {
            "ema20": 0.0017,
            "ema60": 0.0016,
            "ema144": 0.00155,
            "ema250": 0.0015,
            "ema333": 0.00145,
        }
        diagnostics = {
            "buy_check": {
                "ts_score": 0.82,
                "ts_with_boost": 0.87,
                "sr_boost": 0.26,
                "entry_zone_ok": True,
                "slope_ok": True,
                "ts_ok": True,
                "ema60_slope": 0.011,
                "ema144_slope": 0.006,
                "atr": 0.0002,
                "halo": 0.0001,
            },
            "s3_buy_check": {
                "ema250_slope": 0.004,
                "ema333_slope": 0.002,
            },
        }
        scores = {
            "ts": 0.82,
            "dx": 0.58,
            "ox": 0.35,
            "edx": 0.25,
        }
        payload = {
            "state": state,
            "buy_signal": buy_signal,
            "buy_flag": buy_flag,
            "trim_flag": trim_flag,
            "emergency_exit": emergency_exit,
            "first_dip_buy_flag": False,
            "price": 0.0016,
            "ema": ema_values,
            "diagnostics": diagnostics,
            "scores": scores,
        }
        
        # Add exit_position if specified (for S0 transitions)
        if exit_position:
            payload["exit_position"] = True
            payload["exit_reason"] = "test_scenario"
        
        return payload

    def _print_step_summary(self, step_name: str) -> None:
        if not self.position:
            LOGGER.warning("No position after %s", step_name)
            return
        pos = self.position
        exec_history = pos.get("features", {}).get("pm_execution_history") or {}
        print(
            f"\n[{step_name}] position id={pos['id']} status={pos['status']} "
            f"qty={pos.get('total_quantity')} last_s1_buy={exec_history.get('last_s1_buy')}"
        )
        for kind in [
            "uptrend_stage_transition",
            "uptrend_buy_window",
            "uptrend_episode_summary",
            "pm_action",
            "position_closed",
        ]:
            count = self._count_strands(kind)
            print(f"  {kind}: {count} strands since {self.start_ts.isoformat()}")

    def _count_strands(self, kind: str) -> int:
        if not self.position_id:
            return 0
        resp = (
            self.sb.table("ad_strands")
            .select("id", count="exact")
            .eq("kind", kind)
            .eq("position_id", self.position_id)
            .gte("created_at", self.start_ts.isoformat())
            .execute()
        )
        if resp.count is not None:
            return resp.count
        return len(resp.data or [])

    def _sanitize_execution_history(self) -> None:
        if not self.position_id or not self.position:
            return
        features = deepcopy(self.position.get("features") or {})
        exec_history = features.get("pm_execution_history")
        if not isinstance(exec_history, dict):
            return
        cleaned = {k: v for k, v in exec_history.items() if v is not None}
        if cleaned == exec_history:
            return
        features["pm_execution_history"] = cleaned
        self.sb.table("lowcap_positions").update({"features": features}).eq("id", self.position_id).execute()
        self._refresh_position()
    
    def _run_edge_case_tests(self) -> None:
        """Run edge case tests: S2 adds, cooldown, bag-full, partial fills, executor failures."""
        print("\n" + "="*80)
        print("PM ACTION LOOP EDGE CASE TESTS")
        print("="*80)
        
        # Test 1: S2 Add Logic
        print("\n[EDGE CASE 1] S2 Add Logic")
        print("-" * 80)
        self._ensure_watchlist_state()
        # First enter S1 to establish a position
        self._apply_uptrend_state(self._make_uptrend_state("S1", buy_signal=True, buy_flag=False, trim_flag=False, emergency_exit=False))
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        pm_tick.executor = HarnessMockExecutor(pm_tick.sb)
        pm_tick.run()
        self._refresh_position()
        initial_qty = self.position.get("total_quantity", 0.0) if self.position else 0.0
        
        # Now test S2 add
        self._apply_uptrend_state(self._make_uptrend_state("S2", buy_signal=False, buy_flag=True, trim_flag=False, emergency_exit=False))
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        pm_tick.executor = HarnessMockExecutor(pm_tick.sb)
        strands_written = pm_tick.run()
        self._refresh_position()
        final_qty = self.position.get("total_quantity", 0.0) if self.position else 0.0
        
        # Check for add action strand
        add_strands = self._count_strands("pm_action")
        if add_strands > 0 and final_qty > initial_qty:
            print(f"✅ PASS: S2 add logic - quantity increased from {initial_qty} to {final_qty}, {add_strands} pm_action strands")
        else:
            print(f"❌ FAIL: S2 add logic - quantity: {initial_qty} → {final_qty}, strands: {add_strands}")
        
        # Test 2: Cooldown Enforcement (simplified - would need to set last_trim_time)
        print("\n[EDGE CASE 2] Cooldown Enforcement")
        print("-" * 80)
        print("⚠️  SKIPPED: Cooldown test requires setting last_trim_time in execution history")
        print("   (Would need to modify pm_execution_history.last_trim_time)")
        
        # Test 3: Bag-Full Rejection
        print("\n[EDGE CASE 3] Bag-Full Rejection")
        print("-" * 80)
        self._ensure_watchlist_state()
        # Set total_allocation_pct to max (100%)
        if self.position_id:
            self.sb.table("lowcap_positions").update({
                "total_allocation_pct": 100.0,
                "usd_alloc_remaining": 0.0
            }).eq("id", self.position_id).execute()
            self._refresh_position()
        
        self._apply_uptrend_state(self._make_uptrend_state("S1", buy_signal=True, buy_flag=False, trim_flag=False, emergency_exit=False))
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        pm_tick.executor = HarnessMockExecutor(pm_tick.sb)
        pm_tick.run()
        self._refresh_position()
        
        # Check that no entry was made (status should remain watchlist or no quantity increase)
        status_after = self.position.get("status") if self.position else None
        qty_after = self.position.get("total_quantity", 0.0) if self.position else 0.0
        if status_after == "watchlist" or qty_after == 0.0:
            print(f"✅ PASS: Bag-full rejection - status={status_after}, qty={qty_after} (entry skipped)")
        else:
            print(f"⚠️  WARNING: Bag-full may not be enforced - status={status_after}, qty={qty_after}")
        
        # Test 4: Partial Fill Handling
        print("\n[EDGE CASE 4] Partial Fill Handling")
        print("-" * 80)
        self._ensure_watchlist_state()
        # Reset allocation
        if self.position_id:
            self.sb.table("lowcap_positions").update({
                "total_allocation_pct": 10.0,
                "usd_alloc_remaining": 1000.0
            }).eq("id", self.position_id).execute()
            self._refresh_position()
        
        self._apply_uptrend_state(self._make_uptrend_state("S1", buy_signal=True, buy_flag=False, trim_flag=False, emergency_exit=False))
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        pm_tick.executor = HarnessMockExecutor(pm_tick.sb, partial_fill=True)
        pm_tick.run()
        self._refresh_position()
        
        qty_partial = self.position.get("total_quantity", 0.0) if self.position else 0.0
        if qty_partial > 0:
            print(f"✅ PASS: Partial fill handling - quantity={qty_partial} (partial fill applied)")
        else:
            print(f"❌ FAIL: Partial fill handling - no quantity increase")
        
        # Test 5: Executor Failure Path
        print("\n[EDGE CASE 5] Executor Failure Path")
        print("-" * 80)
        self._ensure_watchlist_state()
        qty_before_fail = self.position.get("total_quantity", 0.0) if self.position else 0.0
        
        self._apply_uptrend_state(self._make_uptrend_state("S1", buy_signal=True, buy_flag=False, trim_flag=False, emergency_exit=False))
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        pm_tick.executor = HarnessMockExecutor(pm_tick.sb, fail_mode="entry")
        pm_tick.run()
        self._refresh_position()
        
        qty_after_fail = self.position.get("total_quantity", 0.0) if self.position else 0.0
        if qty_after_fail == qty_before_fail:
            print(f"✅ PASS: Executor failure path - quantity unchanged ({qty_before_fail} → {qty_after_fail})")
        else:
            print(f"❌ FAIL: Executor failure path - quantity changed ({qty_before_fail} → {qty_after_fail})")
        
        # Test 6: Emergency Exit Failure
        print("\n[EDGE CASE 6] Emergency Exit Failure")
        print("-" * 80)
        # First ensure we have a position with quantity
        if not self.position or self.position.get("total_quantity", 0.0) == 0.0:
            # Create a position with quantity
            self._apply_uptrend_state(self._make_uptrend_state("S1", buy_signal=True, buy_flag=False, trim_flag=False, emergency_exit=False))
            pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
            pm_tick.executor = HarnessMockExecutor(pm_tick.sb)
            pm_tick.run()
            self._refresh_position()
        
        qty_before_exit_fail = self.position.get("total_quantity", 0.0) if self.position else 0.0
        
        # Try emergency exit with failing executor
        self._apply_uptrend_state(self._make_uptrend_state("S3", buy_signal=False, buy_flag=False, trim_flag=False, emergency_exit=True))
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        pm_tick.executor = HarnessMockExecutor(pm_tick.sb, fail_mode="exit")
        pm_tick.run()
        self._refresh_position()
        
        qty_after_exit_fail = self.position.get("total_quantity", 0.0) if self.position else 0.0
        status_after_exit_fail = self.position.get("status") if self.position else None
        
        if qty_after_exit_fail == qty_before_exit_fail and status_after_exit_fail == "active":
            print(f"✅ PASS: Emergency exit failure - quantity unchanged ({qty_before_exit_fail} → {qty_after_exit_fail}), status={status_after_exit_fail}")
        else:
            print(f"⚠️  WARNING: Emergency exit failure - quantity: {qty_before_exit_fail} → {qty_after_exit_fail}, status={status_after_exit_fail}")
        
        print("\n" + "="*80)
        print("EDGE CASE TESTS COMPLETE")
        print("="*80 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PM action harness")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    harness = PMActionHarness()
    harness.run()


if __name__ == "__main__":
    main()

