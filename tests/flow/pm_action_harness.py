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
from typing import Any, Dict, List

from dotenv import load_dotenv

from utils.supabase_manager import SupabaseManager
from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from tests.flow.pm_learning_flow_harness import PMLearningFlowHarness


LOGGER = logging.getLogger("pm_action_harness")


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

        for scenario in scenarios:
            LOGGER.info("=== %s ===", scenario["name"])
            
            # Set up position state for this scenario
            if scenario.get("ensure_no_trade"):
                # Clear trade_id and set to watchlist for scenarios that shouldn't have a trade
                self._clear_trade_id()
            elif scenario.get("expected_status") == "active":
                # For entry scenarios, ensure we start from watchlist with no trade_id
                # This allows PM to create a new trade
                self._ensure_watchlist_state()
            
            self._apply_uptrend_state(scenario["uptrend"])
            LOGGER.info("Running pm_core_tick...")
            try:
                strands_written = PMCoreTick(timeframe=self.TEST_TIMEFRAME).run()
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

