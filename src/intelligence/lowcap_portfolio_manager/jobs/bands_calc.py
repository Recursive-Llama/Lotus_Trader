from __future__ import annotations

import os
import math
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


def _hour_bucket(dt: Optional[datetime] = None) -> datetime:
    now = dt or datetime.now(tz=timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _sigmoid(x: float, k: float = 1.2) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-k * x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class BandsCalc:
    """Compute portfolio cut_pressure with core-count seesaw folded in and emit band_breach events."""

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        # Config defaults (can be mirrored via env/pm_config)
        self.ideal_core = int(os.getenv("PM_IDEAL_CORE_COUNT", "12"))
        self.tanh_tau = float(os.getenv("PM_BANDS_TAU", "4"))
        self.tanh_k = float(os.getenv("PM_BANDS_K", "0.25"))

    def _latest_phase_row(self) -> Dict[str, Any]:
        res = (
            self.sb.table("phase_state")
            .select("phase,score,slope,curvature,ts")
            .eq("token", "PORTFOLIO")
            .eq("horizon", "meso")
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else {}

    def _phase_tension(self, score: float, curvature: float) -> float:
        S = float(score or 0.0)
        C = float(curvature or 0.0)
        term = (
            0.6 * _sigmoid(+S)
            + 0.4 * _sigmoid(+S) * _sigmoid(-C)
            - 0.6 * _sigmoid(-S) * _sigmoid(+C)
        )
        return _clip01(term)

    def _core_terms(self, core_count: int) -> tuple[float, float]:
        d = float(core_count - self.ideal_core)
        t = math.tanh(d / max(1e-6, self.tanh_tau))
        core_pressure = _clip01(0.5 + 0.5 * t)
        delta_core = self.tanh_k * t
        return core_pressure, delta_core

    def _latest_dominance(self) -> Dict[str, Any]:
        res = (
            self.sb.table("portfolio_bands")
            .select("ts, dominance_delta")
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else {}

    def _latest_cut_pressure(self) -> float:
        res = (
            self.sb.table("portfolio_bands")
            .select("ts, cut_pressure")
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        try:
            return float((rows[0] or {}).get("cut_pressure") or 0.0)
        except Exception:
            return 0.0

    def _core_count(self) -> int:
        res = (
            self.sb.table("lowcap_positions")
            .select("id")
            .eq("status", "active")
            .limit(10000)
            .execute()
        )
        return len(res.data or [])

    def compute_and_write(self) -> bool:
        ts_hour = _hour_bucket()
        # inputs
        phase_row = self._latest_phase_row()
        S = float(phase_row.get("score") or 0.0)
        C = float(phase_row.get("curvature") or 0.0)
        phase_tension = self._phase_tension(S, C)

        core_count = self._core_count()
        core_pressure, delta_core = self._core_terms(core_count)

        domin = self._latest_dominance()
        dominance_delta = float(domin.get("dominance_delta") or 0.0)

        liquidity_stress = 0.0
        intent_skew = 0.0

        cut_target = _clip01(
            0.55 * phase_tension
            + 0.25 * core_pressure
            + 0.10 * liquidity_stress
            + 0.10 * intent_skew
            + dominance_delta
        )

        prev = self._latest_cut_pressure()
        alpha = 0.15
        cut_pressure = prev + alpha * (cut_target - prev)
        if abs(cut_pressure - prev) > 0.20:
            cut_pressure = prev + 0.20 * (1 if cut_pressure > prev else -1)

        existing = (
            self.sb.table("portfolio_bands")
            .select("*")
            .eq("ts", ts_hour.isoformat())
            .limit(1)
            .execute()
            .data
            or []
        )
        row: Dict[str, Any] = existing[0].copy() if existing else {"ts": ts_hour.isoformat()}
        row.update(
            {
                "core_count": core_count,
                "core_pressure": core_pressure,
                "cut_pressure_raw": cut_target,
                "cut_pressure": cut_pressure,
                "phase_tension": phase_tension,
                "dominance_delta": dominance_delta,
                "delta_core": delta_core,
            }
        )
        try:
            self.sb.table("portfolio_bands").upsert([row], on_conflict="ts").execute()
            logger.info(
                "bands_calc ts=%s core=%d cut=%.3f target=%.3f",
                ts_hour.isoformat(),
                core_count,
                cut_pressure,
                cut_target,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("bands_calc write failed: %s", exc)
            return False


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    BandsCalc().compute_and_write()


if __name__ == "__main__":
    main()
