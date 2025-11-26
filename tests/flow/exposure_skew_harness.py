"""
Exposure Skew Harness
=====================

Creates multiple overlapping positions to force the exposure lookup to detect
crowding, then runs `pm_core_tick` (with the mock executor) and asserts that
the resulting `pm_action` strand shows an `exposure_skew` multiplier below 1.0.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

from src.intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from tests.flow.pm_action_harness import HarnessMockExecutor

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
    return {
        "state": state,
        "buy_signal": True,
        "buy_flag": False,
        "first_dip_buy_flag": False,
        "trim_flag": False,
        "emergency_exit": False,
        "price": 0.0015,
        "ema": {
            "ema20": 0.0014,
            "ema60": 0.0013,
            "ema144": 0.0012,
            "ema333": 0.0011,
        },
        "diagnostics": {
            "buy_check": {
                "entry_zone_ok": True,
                "ts_score": 0.82,
                "ts_with_boost": 0.87,
                "ts_ok": True,
                "slope_ok": True,
                "halo": 0.0001,
            }
        },
        "scores": {
            "ts": 0.82,
            "dx": 0.65,
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

    def run(self) -> None:
        self._cleanup_positions()
        try:
            peer_a = self._insert_position(TEST_CONTRACTS[1], allocation_pct=30.0, pattern_key="pm.uptrend.S1.peer_a")
            peer_b = self._insert_position(TEST_CONTRACTS[2], allocation_pct=35.0, pattern_key="pm.uptrend.S1.peer_b")
            target = self._insert_position(TEST_CONTRACTS[0], allocation_pct=40.0, pattern_key="pm.uptrend.S1.target")
            logger.info("Seeded positions: target=%s peers=%s,%s", target, peer_a, peer_b)

            self._arm_target_for_entry(target)
            pm = PMCoreTick(timeframe="1h")
            pm.executor = HarnessMockExecutor(pm.sb)
            pm.run()

            skew = self._fetch_latest_exposure_skew(target)
            if skew is None:
                raise RuntimeError("No pm_action strand recorded for target position")
            logger.info("Exposure skew applied: %.4f", skew)
            if skew >= 1.0:
                raise RuntimeError(f"Expected exposure_skew < 1.0, observed {skew:.4f}")
            logger.info("✅ Exposure skew harness PASSED (skew=%.4f)", skew)
        finally:
            self._cleanup_positions()

    def _cleanup_positions(self) -> None:
        for contract in TEST_CONTRACTS:
            try:
                self.sb.table("lowcap_positions").delete().eq("token_contract", contract).execute()
            except Exception:
                pass

    def _insert_position(self, token_contract: str, allocation_pct: float, pattern_key: str) -> str:
        position_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        entry_context = {**SCOPE_TEMPLATE, "pattern_key": pattern_key, "chain": "solana"}
        features = {
            "uptrend_engine_v4": _make_uptrend_state("S0"),
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
            "status": "active",
            "current_trade_id": str(uuid.uuid4()),
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
            return None
        content = rows[0].get("content") or {}
        multipliers = content.get("learning_multipliers") or {}
        skew = multipliers.get("exposure_skew")
        return float(skew) if skew is not None else None


def main() -> None:
    harness = ExposureSkewHarness()
    harness.run()


if __name__ == "__main__":
    main()

