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
    Thin wrapper around PMExecutor for live execution.
    Uses percentage-based allocation (no USD cap).
    Stores the last execution result for harness reporting.
    """

    def __init__(self, sb_client) -> None:
        super().__init__(trader=None, sb_client=sb_client)
        self.last_result: Dict[str, Any] | None = None
        self.last_decision: Dict[str, Any] | None = None

    def execute(self, decision: Dict[str, Any], position: Dict[str, Any]) -> Dict[str, Any]:
        decision_type = (decision.get("decision_type") or "").lower()
        decision_copy = dict(decision)
        position_copy = dict(position)

        # No USD cap - use percentage-based allocation as-is
        # The position already has usd_alloc_remaining set from _set_allocation_caps()

        self.last_decision = decision_copy
        result = super().execute(decision_copy, position_copy)
        self.last_result = result
        return result


class ExecutorSmokeHarness(PMActionHarness):
    TEST_TICKER_ENV = "PM_CANARY_SYMBOLS"
    # Always use Solana USDC balance for allocation calculations (portfolio base)
    ALLOCATION_BASE_CHAIN = "solana"

    def __init__(self, *, mode: str, allocation_pct: float, run_buy: bool, run_sell: bool, 
                 token_contract: Optional[str] = None, token_chain: Optional[str] = None):
        super().__init__()
        self.mode = mode
        self.allocation_pct = max(0.01, min(100.0, allocation_pct))  # Clamp between 0.01% and 100%
        self.run_buy = run_buy
        self.run_sell = run_sell
        # Override test token/chain if provided
        if token_contract:
            self.TEST_CONTRACT = token_contract
        if token_chain:
            self.TEST_CHAIN = token_chain.lower()
        os.environ.setdefault("MIN_BRIDGE_USD", "1.0")
        os.environ.setdefault("NATIVE_GAS_THRESHOLD_USD", "1.0")
        os.environ.setdefault("INITIAL_NATIVE_GAS_USD", "1.0")

    def _ensure_position(self) -> None:
        """Override to create position directly for specified token/chain."""
        self._refresh_position()
        if self.position:
            LOGGER.info(
                "Found existing position id=%s status=%s",
                self.position_id,
                self.position.get("status"),
            )
            return

        LOGGER.info("No %s position found for %s on %s – creating directly", 
                   self.TEST_TIMEFRAME, self.TEST_CONTRACT, self.TEST_CHAIN)
        
        # Create position directly
        import uuid
        from datetime import datetime, timezone
        
        position_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        # Get token ticker from contract (last 4 chars) or use contract
        ticker = self.TEST_CONTRACT[-4:] if len(self.TEST_CONTRACT) > 4 else self.TEST_CONTRACT[:4]
        
        payload = {
            "id": position_id,
            "token_contract": self.TEST_CONTRACT,
            "token_chain": self.TEST_CHAIN,
            "token_ticker": ticker,
            "timeframe": self.TEST_TIMEFRAME,
            "status": "watchlist",
            "state": "S4",
            "current_trade_id": None,
            "total_allocation_pct": 0.0,  # Will be set by _set_allocation_caps
            "total_allocation_usd": 0.0,
            "total_extracted_usd": 0.0,
            "usd_alloc_remaining": 0.0,
            "total_quantity": 0.0,
            "total_tokens_bought": 0.0,
            "total_tokens_sold": 0.0,
            "features": {
                "uptrend_engine_v4": {
                    "state": "S4",
                    "price": 0.0,
                },
                "pm_execution_history": {},
            },
            "created_at": now,
            "updated_at": now,
        }
        
        self.sb.table("lowcap_positions").insert(payload).execute()
        LOGGER.info("Created position id=%s for %s on %s", position_id, self.TEST_CONTRACT, self.TEST_CHAIN)
        self._refresh_position()
        
        if not self.position:
            raise RuntimeError(f"Failed to create test position for {self.TEST_CONTRACT} on {self.TEST_CHAIN}")

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
        result = self._execute_with_state(uptrend_state, expect_action="entry")
        # Add database verification after buy
        if self.mode == "live" and result.get("executor_result", {}).get("status") == "success":
            result["db_verification"] = self._verify_database_after_buy()
        return result

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
        """Set allocation based on percentage of Solana USDC balance (portfolio base)."""
        if not self.position_id:
            return
        
        # Always use Solana USDC balance for allocation calculation (portfolio base)
        wallet_result = (
            self.sb.table("wallet_balances")
            .select("usdc_balance,balance_usd")
            .eq("chain", self.ALLOCATION_BASE_CHAIN.lower())
            .limit(1)
            .execute()
        )
        
        if not wallet_result.data:
            LOGGER.warning(f"No wallet_balances row found for chain={self.ALLOCATION_BASE_CHAIN}, using 0.0")
            solana_usdc_balance = 0.0
        else:
            row = wallet_result.data[0]
            solana_usdc_balance = float(row.get("usdc_balance") or row.get("balance_usd") or 0.0)
        
        # Calculate allocation from percentage
        max_allocation_usd = solana_usdc_balance * (self.allocation_pct / 100.0)
        
        LOGGER.info(f"=== Allocation Calculation ===")
        LOGGER.info(f"Portfolio base chain: {self.ALLOCATION_BASE_CHAIN}")
        LOGGER.info(f"Solana USDC balance: ${solana_usdc_balance:,.2f}")
        LOGGER.info(f"Allocation percentage: {self.allocation_pct}%")
        LOGGER.info(f"Max allocation USD: ${max_allocation_usd:,.2f}")
        LOGGER.info(f"Position chain: {self.TEST_CHAIN}")
        LOGGER.info(f"==============================")
        
        update = {
            "total_allocation_pct": self.allocation_pct,
        }
        
        # If the position is empty (watchlist + zero quantity), clear historical allocation
        current_quantity = float(self.position.get("total_quantity") or 0.0)
        if current_quantity == 0 and self.position.get("status") == "watchlist":
            update["total_allocation_usd"] = 0.0
            update["total_extracted_usd"] = 0.0
            update["usd_alloc_remaining"] = max_allocation_usd
        else:
            # For existing positions, calculate remaining allocation
            current_allocation = float(self.position.get("total_allocation_usd") or 0.0)
            current_extracted = float(self.position.get("total_extracted_usd") or 0.0)
            net_deployed = current_allocation - current_extracted
            update["usd_alloc_remaining"] = max(0.0, max_allocation_usd - net_deployed)
            LOGGER.info(f"Existing position: deployed=${net_deployed:,.2f}, remaining=${update['usd_alloc_remaining']:,.2f}")
        
        self.sb.table("lowcap_positions").update(update).eq("id", self.position_id).execute()
        self._refresh_position()

    def _execute_with_state(self, uptrend: Dict[str, Any], expect_action: Optional[str]) -> Dict[str, Any]:
        self._apply_uptrend_state(uptrend)
        pm_tick = PMCoreTick(timeframe=self.TEST_TIMEFRAME)
        preview = self._preview_actions(pm_tick)

        if self.mode == "live":
            executor = LiveMicroExecutor(pm_tick.sb)
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
            # Store executor result for verification
            self._last_executor_result = executor.last_result or {}
        else:
            result_summary["executor_result"] = "mock"
            self._last_executor_result = {}

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

    def _verify_database_after_buy(self) -> Dict[str, Any]:
        """Verify database fields are correct after a buy execution."""
        if not self.position_id:
            return {"error": "no_position_id"}
        
        self._refresh_position()
        if not self.position:
            return {"error": "position_not_found"}
        
        exec_result = getattr(self, "_last_executor_result", {})
        tokens_bought = float(exec_result.get("tokens_bought", 0.0))
        notional_usd = float(exec_result.get("notional_usd", 0.0))
        price = float(exec_result.get("price", 0.0))
        
        # Get current position values
        db_total_quantity = float(self.position.get("total_quantity") or 0.0)
        db_total_allocation_usd = float(self.position.get("total_allocation_usd") or 0.0)
        db_total_tokens_bought = float(self.position.get("total_tokens_bought") or 0.0)
        db_avg_entry_price = float(self.position.get("avg_entry_price") or 0.0) if self.position.get("avg_entry_price") is not None else 0.0
        
        verification = {
            "executor": {
                "tokens_bought": tokens_bought,
                "notional_usd": notional_usd,
                "price": price,
            },
            "database": {
                "total_quantity": db_total_quantity,
                "total_allocation_usd": db_total_allocation_usd,
                "total_tokens_bought": db_total_tokens_bought,
                "avg_entry_price": db_avg_entry_price,
            },
            "checks": {
                "quantity_matches": abs(db_total_quantity - tokens_bought) < 0.0001 if tokens_bought > 0 else True,
                "allocation_matches": abs(db_total_allocation_usd - notional_usd) < 0.01 if notional_usd > 0 else True,
                "tokens_bought_matches": abs(db_total_tokens_bought - tokens_bought) < 0.0001 if tokens_bought > 0 else True,
                "avg_price_reasonable": db_avg_entry_price > 0 and abs(db_avg_entry_price - price) < (price * 0.1) if price > 0 else False,
            }
        }
        
        # Calculate expected avg_entry_price
        if db_total_tokens_bought > 0:
            expected_avg = db_total_allocation_usd / db_total_tokens_bought
            verification["checks"]["avg_price_correct"] = abs(db_avg_entry_price - expected_avg) < 0.0001
        else:
            verification["checks"]["avg_price_correct"] = False
        
        return verification


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PM executor smoke harness")
    parser.add_argument("--mode", choices=["dry-run", "live"], default="dry-run", help="Use mock executor or live Li.Fi executor")
    parser.add_argument("--allocation-pct", type=float, default=2.0, help="Allocation percentage of Solana USDC balance (default: 2.0%%)")
    parser.add_argument("--skip-buy", action="store_true", help="Skip the buy leg")
    parser.add_argument("--skip-sell", action="store_true", help="Skip the sell leg")
    parser.add_argument("--token-contract", type=str, help="Token contract address to test (overrides default)")
    parser.add_argument("--token-chain", type=str, help="Token chain (base, solana, ethereum, bsc) - overrides default")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    harness = ExecutorSmokeHarness(
        mode=args.mode,
        allocation_pct=args.allocation_pct,
        run_buy=not args.skip_buy,
        run_sell=not args.skip_sell,
        token_contract=args.token_contract,
        token_chain=args.token_chain,
    )
    summary = harness.run()
    LOGGER.info("Executor smoke summary: %s", summary)
    print(summary)


if __name__ == "__main__":
    main()

