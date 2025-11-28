"""
Exposure Skew Harness
=====================

Creates multiple overlapping positions to force the exposure lookup to detect
crowding, then runs `pm_core_tick` (with the mock executor) and asserts that
the resulting `pm_action` strand shows an `exposure_skew` multiplier below 1.0.
"""

from __future__ import annotations

import logging
import math
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from supabase import create_client, Client

# Ensure project root is on sys.path when running as a script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from src.intelligence.lowcap_portfolio_manager.pm.exposure import (
    ExposureConfig,
    ExposureLookup,
)
from src.intelligence.lowcap_portfolio_manager.pm.overrides import clear_override_cache

try:
from tests.flow.pm_action_harness import HarnessMockExecutor
except ModuleNotFoundError:  # pragma: no cover
    from pm_action_harness import HarnessMockExecutor

logger = logging.getLogger("exposure_skew_harness")

load_dotenv()

TEST_CONTRACTS = [
    "EXPOZ_TARGET",
    "EXPOZ_PEER_A",
    "EXPOZ_PEER_B",
]

SCOPE_TEMPLATE = {
    "curator": "expo_harness",
    "chain": "solana",
    "mcap_bucket": "micro",
    "vol_bucket": "low",
    "age_bucket": "new",
    "intent": "test_case",
    "mcap_vol_ratio_bucket": "high",
    "market_family": "lowcaps",
    "A_mode": "aggressive",
    "E_mode": "patient",
}


def _make_uptrend_state(state: str = "S1") -> dict:
    price = 0.0015
    ema60 = 0.00148
    atr_val = 0.00005
    return {
        "state": state,
        "buy_signal": True,
        "buy_flag": False,
        "first_dip_buy_flag": False,
        "trim_flag": False,
        "emergency_exit": False,
        "price": price,
        "ema": {
            "ema20": 0.0014,
            "ema60": ema60,
            "ema144": 0.00135,
            "ema333": 0.00125,
        },
        "diagnostics": {
            "buy_check": {
                "entry_zone_ok": True,
                "ts_score": 0.9,
                "ts_with_boost": 0.92,
                "ts_ok": True,
                "slope_ok": True,
                "halo": 0.5,
                "atr": atr_val,
            }
        },
        "scores": {
            "ts": 0.9,
            "dx": 0.72,
            "ox": 0.4,
            "edx": 0.35,
        },
    }


class ExposureSkewHarness:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        self.sb: Client = create_client(url, key)
        logging.basicConfig(level=logging.INFO)

        self._override_pattern_keys: List[str] = []

    def run(self) -> None:
        """Execute all exposure/skew stress tests."""
        tests = [
            ("Partial scope handling → neutral multiplier", self._test_partial_scope_handling),
            ("Extreme configs (empty masks / high alpha)", self._test_extreme_configs),
            ("Mask weighting configs (zero weights / alpha=0)", self._test_mask_weighting_configs),
            ("Crowding reduces exposure_skew < 1.0", self._test_crowding_exposure),
            ("Skew × strength interaction (override damped by exposure)", self._test_skew_strength_interaction),
        ]

        failures: List[str] = []
        for name, fn in tests:
            logger.info("🔬 Running test: %s", name)
            try:
                fn()
                logger.info("✅ PASS: %s", name)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{name}: {exc}")
                logger.exception("❌ FAIL: %s", name)
        self._cleanup_positions()
        self._cleanup_overrides()
        clear_override_cache()
        if failures:
            raise RuntimeError("Exposure harness failures:\n- " + "\n- ".join(failures))

    def _cleanup_positions(self) -> None:
        for contract in TEST_CONTRACTS:
            try:
                self.sb.table("lowcap_positions").delete().eq("token_contract", contract).execute()
            except Exception:
                pass

    def _cleanup_overrides(self) -> None:
        if not self._override_pattern_keys:
            return
        try:
            self.sb.table("pm_overrides").delete().in_("pattern_key", self._override_pattern_keys).execute()
        except Exception:
            pass
        self._override_pattern_keys.clear()

    def _insert_position(self, token_contract: str, allocation_pct: float, pattern_key: str) -> str:
        position_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        entry_context = {**SCOPE_TEMPLATE, "pattern_key": pattern_key, "chain": "solana"}
        base_state = _make_uptrend_state("S0")
        features = {
            "uptrend_engine_v4": base_state,
            "pm_execution_history": {},
            "pattern_key": pattern_key,
        }
        usd_alloc = allocation_pct * 1000.0
        payload = {
            "id": position_id,
            "token_contract": token_contract,
            "token_chain": "solana",
            "token_ticker": token_contract[-4:],
            "timeframe": "1h",
            "status": "watchlist",
            "current_trade_id": None,
            "total_allocation_pct": allocation_pct,
            "total_allocation_usd": usd_alloc,
            "usd_alloc_remaining": usd_alloc,
            "total_quantity": 0.0,
            "entry_context": entry_context,
            "features": features,
            "created_at": now,
            "updated_at": now,
        }
        self.sb.table("lowcap_positions").insert(payload).execute()
        return position_id

    def _arm_target_for_entry(self, position_id: str) -> None:
        res = self.sb.table("lowcap_positions").select("features,total_allocation_usd").eq("id", position_id).single().execute()
        features = res.data.get("features") or {}
        features["uptrend_engine_v4"] = _make_uptrend_state("S1")
        features["pm_execution_history"] = {"prev_state": "S0"}
        usd_alloc = res.data.get("total_allocation_usd", 40000.0)
        payload = {
            "features": features,
            "total_quantity": 0.0,
            "total_allocation_usd": usd_alloc,
            "total_extracted_usd": 0.0,
            "usd_alloc_remaining": usd_alloc,
            "status": "watchlist",
            "current_trade_id": None,
        }
        self.sb.table("lowcap_positions").update(payload).eq("id", position_id).execute()

    def _fetch_latest_exposure_skew(self, position_id: str) -> float | None:
        res = (
            self.sb.table("ad_strands")
            .select("content")
            .eq("kind", "pm_action")
            .eq("position_id", position_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            logger.warning("No pm_action strands found for position %s", position_id)
            return None
        content = rows[0].get("content") or {}
        logger.info("Latest pm_action content: %s", content)
        multipliers = content.get("learning_multipliers") or {}
        skew = multipliers.get("exposure_skew")
        if skew is None:
            skew = (content.get("reasons") or {}).get("exposure_skew")
        return float(skew) if skew is not None else None

    # ----------------------------
    # Pure ExposureLookup tests
    # ----------------------------

    def _sample_positions(self, missing_fields: bool = False) -> List[Dict[str, Any]]:
        """Build synthetic positions for ExposureLookup tests."""
        positions: List[Dict[str, Any]] = []
        for idx in range(3):
            entry = {
                **SCOPE_TEMPLATE,
                "curator": f"curator_{idx}",
                "pattern_key": f"sample_pattern_{idx}",
            }
            if missing_fields and idx == 1:
                entry.pop("intent", None)
            if missing_fields and idx == 2:
                entry.pop("mcap_bucket", None)
            positions.append(
                {
                    "total_allocation_pct": 10.0 * (idx + 1),
                    "entry_context": entry,
                    "features": {"pattern_key": entry["pattern_key"]},
                    "timeframe": "1h",
                }
            )
        return positions

    def _test_partial_scope_handling(self) -> None:
        cfg = ExposureConfig.from_pm_config({})
        lookup = ExposureLookup.build(self._sample_positions(missing_fields=True), cfg)
        scope = {"curator": "partial_case", "chain": "solana"}  # Missing dims
        result = lookup.lookup("pattern_partial", scope)
        if not math.isclose(result, 1.0, abs_tol=1e-6):
            raise AssertionError(f"Expected neutral multiplier 1.0 for partial scope, got {result}")

    def _test_extreme_configs(self) -> None:
        positions = self._sample_positions()
        cfg_empty_masks = ExposureConfig.from_pm_config({"exposure_skew": {"mask_defs": []}})
        lookup_empty = ExposureLookup.build(positions, cfg_empty_masks)
        res_empty = lookup_empty.lookup("pattern_extreme", SCOPE_TEMPLATE)
        if abs(res_empty - 1.0) > 0.2:
            raise AssertionError(f"Empty mask config should stay near-neutral, got {res_empty}")

        cfg_high_alpha = ExposureConfig.from_pm_config({"exposure_skew": {"alpha": 5.0}})
        lookup_alpha = ExposureLookup.build(positions, cfg_high_alpha)
        res_alpha = lookup_alpha.lookup("pattern_extreme", SCOPE_TEMPLATE)
        if not (0.33 <= res_alpha <= 1.33):
            raise AssertionError(f"High alpha multiplier out of bounds: {res_alpha}")

    def _test_mask_weighting_configs(self) -> None:
        zero_weights = {dim: 0.0 for dim in SCOPE_TEMPLATE.keys()}
        cfg_zero = ExposureConfig.from_pm_config({"exposure_skew": {"scope_dim_weights": zero_weights}})
        lookup_zero = ExposureLookup.build(self._sample_positions(), cfg_zero)
        res_zero = lookup_zero.lookup("pattern_zero", SCOPE_TEMPLATE)
        if not (0.33 <= res_zero <= 1.33):
            raise AssertionError(f"Zero weights produced invalid multiplier: {res_zero}")

        cfg_alpha_zero = ExposureConfig.from_pm_config({"exposure_skew": {"alpha": 0.0}})
        lookup_alpha_zero = ExposureLookup.build(self._sample_positions(), cfg_alpha_zero)
        res_alpha_zero = lookup_alpha_zero.lookup("pattern_alpha0", SCOPE_TEMPLATE)
        if not (0.33 <= res_alpha_zero <= 1.33):
            raise AssertionError(f"Alpha=0 config produced invalid multiplier: {res_alpha_zero}")

    # ----------------------------
    # Flow-based PM harness tests
    # ----------------------------

    def _seed_positions_for_target(self) -> str:
        """Seed peers + target positions for flow tests."""
        self._cleanup_positions()
        peer_a = self._insert_position(
            TEST_CONTRACTS[1], allocation_pct=30.0, pattern_key="pm.uptrend.S1.peer_a"
        )
        peer_b = self._insert_position(
            TEST_CONTRACTS[2], allocation_pct=35.0, pattern_key="pm.uptrend.S1.peer_b"
        )
        target = self._insert_position(
            TEST_CONTRACTS[0], allocation_pct=40.0, pattern_key="pm.uptrend.S1.target"
        )
        logger.info("Seeded positions: target=%s peers=%s,%s", target, peer_a, peer_b)
        self._arm_target_for_entry(target)
        return target

    def _run_pm_core(self) -> None:
        pm = PMCoreTick(timeframe="1h")
        pm.executor = HarnessMockExecutor(pm.sb)
        pm.run()

    def _test_crowding_exposure(self) -> None:
        target = self._seed_positions_for_target()
        self._run_pm_core()
        skew = self._fetch_latest_exposure_skew(target)
        if skew is None:
            raise AssertionError("No pm_action strand recorded for target position")
        if skew >= 1.0:
            raise AssertionError(f"Expected exposure_skew < 1.0, observed {skew:.4f}")

    def _test_skew_strength_interaction(self) -> None:
        target = self._seed_positions_for_target()
        # Insert a 3x strength override for the target pattern
        override_key = "module=pm|pattern_key=uptrend.S1.unknown"
        payload = {
            "pattern_key": override_key,
            "action_category": "entry",
            "scope_subset": {"chain": "solana", "timeframe": "1h"},
            "multiplier": 3.0,
            "confidence_score": 0.95,
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sb.table("pm_overrides").upsert(payload, on_conflict="pattern_key,action_category,scope_subset").execute()
        self._override_pattern_keys.append(override_key)

        self._run_pm_core()
        res = (
            self.sb.table("ad_strands")
            .select("content")
            .eq("kind", "pm_action")
            .eq("position_id", target)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise AssertionError("pm_action strand missing for override test")
        content = rows[0].get("content") or {}
        learning_mults = content.get("learning_multipliers") or {}
        size_mult = float(learning_mults.get("pm_strength", 0.0))
        exposure_skew = float(learning_mults.get("exposure_skew", 1.0))
        combined = float(learning_mults.get("combined_multiplier", size_mult * exposure_skew))

        if size_mult < 1.5:
            raise AssertionError(f"Expected pm_strength boost >1.5x, got {size_mult:.2f}")
        if exposure_skew >= 1.0:
            raise AssertionError(f"Expected exposure skew < 1.0 with crowding, got {exposure_skew:.2f}")
        if abs(combined - (size_mult * exposure_skew)) > 0.05:
            raise AssertionError(
                f"Combined multiplier mismatch: combined={combined:.2f} size*skew={(size_mult * exposure_skew):.2f}"
            )


def main() -> None:
    harness = ExposureSkewHarness()
    harness.run()


if __name__ == "__main__":
    main()

