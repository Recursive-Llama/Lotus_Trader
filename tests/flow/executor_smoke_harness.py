"""
Executor smoke test harness.

Goals:
1. Drive PM Core Tick with real uptrend states so it emits a buy (entry) and sell (emergency exit) in sequence.
2. Optionally route through the live PM executor (Li.Fi) with a micro USD cap so we can verify on-chain plumbing.
3. Capture the resulting `pm_action` strands and executor payloads for evidence.

Usage:
    PYTHONPATH=src:. python tests/flow/executor_smoke_harness.py --mode dry-run
    PYTHONPATH=src:. python tests/flow/executor_smoke_harness.py --mode live --max-usd 5
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Ensure repo root is importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

try:
    from tests.flow.pm_action_harness import PMActionHarness, HarnessMockExecutor
except ModuleNotFoundError:  # pragma: no cover
    from pm_action_harness import PMActionHarness, HarnessMockExecutor

from src.intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from src.intelligence.lowcap_portfolio_manager.pm.executor import PMExecutor
from src.intelligence.lowcap_portfolio_manager.pm.config import (
    load_pm_config,
    fetch_and_merge_db_config,
)
from src.intelligence.lowcap_portfolio_manager.pm.levers import compute_levers
from src.intelligence.lowcap_portfolio_manager.pm.actions import plan_actions_v4


LOGGER = logging.getLogger("executor_smoke_harness")
load_dotenv()


class LiveMicroExecutor(PMExecutor):
    """
    Thin wrapper around PMExecutor that clamps buy size to a target USD amount.
    Stores the last execution result for harness reporting.
    """

    def __init__(self, sb_client, usd_cap: float) -> None:
        super().__init__(trader=None, sb_client=sb_client)
        self.usd_cap = max(0.1, usd_cap)
        self.last_result: Dict[str, Any] | None = None
        self.last_decision: Dict[str, Any] | None = None

    def execute(self, decision: Dict[str, Any], position: Dict[str, Any]) -> Dict[str, Any]:
        decision_type = (decision.get("decision_type") or "").lower()
        decision_copy = dict(decision)
        position_copy = dict(position)

        if decision_type in {"entry", "add", "trend_add"}:
            size_frac = float(decision_copy.get("size_frac") or 0.0)
            if size_frac <= 0:
                result = {
                    "status": "error",
                    "error": f"Size fraction <= 0 for decision {decision_type}",
                    "decision": decision_copy,
                }
                self.last_result = result
                self.last_decision = decision_copy
                return result
            # Adjust usd_alloc_remaining so notional == usd_cap (size_frac * alloc = usd_cap)
            desired_alloc = self.usd_cap / size_frac
            position_copy["usd_alloc_remaining"] = max(desired_alloc, self.usd_cap)

        self.last_decision = decision_copy
        result = super().execute(decision_copy, position_copy)
        self.last_result = result
        return result


class ExecutorSmokeHarness(PMActionHarness):
    TEST_TICKER_ENV = "PM_CANARY_SYMBOLS"

    def __init__(self, *, mode: str, max_usd: float, run_buy: bool, run_sell: bool):
        super().__init__()
        self.mode = mode
        self.max_usd = max(0.5, max_usd)
        self.run_buy = run_buy
        self.run_sell = run_sell
        os.environ.setdefault("MIN_BRIDGE_USD", f"{self.max_usd}")
        os.environ.setdefault("NATIVE_GAS_THRESHOLD_USD", "1.0")
        os.environ.setdefault("INITIAL_NATIVE_GAS_USD", "1.0")

    def run(self) -> Dict[str, Any]:
        self._ensure_position()
        if not self.position:
            raise RuntimeError("Smoke harness could not locate or create test position")

        ticker = (self.position.get("token_ticker") or "").upper()
        if ticker:
            os.environ[self.TEST_TICKER_ENV] = ticker

        summary: Dict[str, Any] = {"token": ticker, "position_id": self.position_id}

        if self.run_buy:
            summary["buy"] = self._run_buy_smoke()

        if self.run_sell:
            summary["sell"] = self._run_sell_smoke()

        return summary

    def _run_buy_smoke(self) -> Dict[str, Any]:
        LOGGER.info("=== Live executor BUY smoke ===")
        self._ensure_watchlist_state()
        self._set_allocation_caps()
        self._reset_execution_history_for_buy()
        uptrend_state = self._make_uptrend_state(
            "S1",
            buy_signal=True,
            buy_flag=False,
            trim_flag=False,
            emergency_exit=False,
        )
        return self._execute_with_state(uptrend_state, expect_action="entry")

    def _run_sell_smoke(self) -> Dict[str, Any]:
        LOGGER.info("=== Live executor SELL smoke ===")
        self._refresh_position()
        total_qty = float(self.position.get("total_quantity") or 0.0) if self.position else 0.0
        if total_qty <= 0:
            return {
                "skipped": True,
                "reason": "no_inventory",
            }
        uptrend_state = self._make_uptrend_state(
            "S3",
            buy_signal=False,
            buy_flag=False,
            trim_flag=False,
            emergency_exit=True,
            exit_position=True,
        )
        return self._execute_with_state(uptrend_state, expect_action="emergency_exit")

    def _set_allocation_caps(self) -> None:
        if not self.position_id:
            return
        update = {
            "total_allocation_pct": max(0.01, float(self.position.get("total_allocation_pct") or 0.01)),
        }
        wallet = self.sb.table("wallet_balances").select("balance_usd").eq("chain", self.TEST_CHAIN).limit(1).execute()
        balance_usd = float((wallet.data or [{}])[0].get("balance_usd") or 0.0)
        alloc_pct = update["total_allocation_pct"]
        max_allocation_usd = balance_usd * (alloc_pct / 100.0)
        update["total_allocation_usd"] = max_allocation_usd
        update["usd_alloc_remaining"] = max_allocation_usd
        # If the slot is empty (watchlist + zero quantity) clear historical allocation so
        # the next entry reflects only the live notional we send through the executor.
        self.sb.table("lowcap_positions").update(update).eq("id", self.position_id).execute()
        self._refresh_position()

    def _execute_with_state(self, uptrend: Dict[str, Any], expect_action: Optional[str]) -> Dict[str, Any]:
        self._apply_uptrend_state(uptrend)
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        preview = self._preview_actions(pm_tick)

        if self.mode == "live":
            executor = LiveMicroExecutor(pm_tick.sb, usd_cap=self.max_usd)
        else:
            executor = HarnessMockExecutor(pm_tick.sb)
        pm_tick.executor = executor

        strands_written = pm_tick.run()
        self._refresh_position()
        strand = self._fetch_latest_pm_action()

        result_summary = {
            "strands_written": strands_written,
            "position_status": self.position.get("status") if self.position else None,
            "pm_action": strand,
            "mode": self.mode,
            "preview": preview,
        }

        if isinstance(executor, LiveMicroExecutor):
            result_summary["executor_result"] = executor.last_result
            result_summary["decision"] = executor.last_decision
        else:
            result_summary["executor_result"] = "mock"

        if expect_action and strand:
            observed = (strand.get("content") or {}).get("decision_type")
            result_summary["expected_action"] = expect_action
            result_summary["observed_action"] = observed

        return result_summary

    def _reset_execution_history_for_buy(self) -> None:
        """Clear last-buy markers so S1 entries are eligible."""
        if not self.position_id or not self.position:
            return
        features = deepcopy(self.position.get("features") or {})
        exec_history = features.get("pm_execution_history")
        if not isinstance(exec_history, dict):
            return
        mutated = False
        for key in ["last_s1_buy", "last_s2_buy", "last_s3_buy", "last_reclaim_buy"]:
            if key in exec_history:
                exec_history.pop(key, None)
                mutated = True
        if mutated:
            features["pm_execution_history"] = exec_history
            self.sb.table("lowcap_positions").update({"features": features}).eq("id", self.position_id).execute()
            self._refresh_position()

    def _preview_actions(self, pm_tick: PMCoreTick) -> Dict[str, Any]:
        """Compute levers + plan_actions_v4 outcome for debugging."""
        if not self.position:
            return {}

        try:
            regime_context = pm_tick._get_regime_context()
            pm_cfg = load_pm_config()
            pm_cfg = fetch_and_merge_db_config(pm_cfg, pm_tick.sb)
            bucket_cfg = pm_cfg.get("bucket_order_multipliers") or {}

            meso = pm_tick._latest_phase()
            phase = meso.get("phase") or ""
            macro = (regime_context.get("macro") or {}).get("phase") or ""
            cp = pm_tick._latest_cut_pressure()

            token_key = (self.position.get("token_contract"), self.position.get("token_chain"))
            token_bucket = pm_tick._fetch_token_buckets([token_key]).get(token_key)

            levers = compute_levers(
                macro,
                phase,
                cp,
                self.position.get("features") or {},
                bucket_context=regime_context,
                position_bucket=token_bucket,
                bucket_config=bucket_cfg,
            )

            actions = plan_actions_v4(
                self.position,
                float(levers.get("A_value", 0.0)),
                float(levers.get("E_value", 0.0)),
                phase,
                pm_tick.sb,
                regime_context=regime_context,
                token_bucket=token_bucket,
                feature_flags=pm_cfg.get("feature_flags", {}),
                exposure_lookup=None,
            )

            return {
                "phase": phase,
                "cut_pressure": cp,
                "levers": levers,
                "actions": actions,
            }
        except Exception as exc:  # pragma: no cover - diagnostics only
            LOGGER.warning("Action preview failed: %s", exc)
            return {"error": str(exc)}

    def _fetch_latest_pm_action(self) -> Optional[Dict[str, Any]]:
        if not self.position_id:
            return None
        resp = (
            self.sb.table("ad_strands")
            .select("id, content, created_at")
            .eq("kind", "pm_action")
            .eq("position_id", self.position_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PM executor smoke harness")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run", help="Use mock executor or live Li.Fi executor")
    parser.add_argument("--max-usd", type=float, default=1.0, help="Target USD notional for micro trades (buy leg)")
    parser.add_argument("--skip-buy", action="store_true", help="Skip the buy leg")
    parser.add_argument("--skip-sell", action="store_true", help="Skip the sell leg")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    harness = ExecutorSmokeHarness(
        mode=args.mode,
        max_usd=args.max_usd,
        run_buy=not args.skip_buy,
        run_sell=not args.skip_sell,
    )
    summary = harness.run()
    LOGGER.info("Executor smoke summary: %s", summary)
    print(summary)


if __name__ == "__main__":
    main()

