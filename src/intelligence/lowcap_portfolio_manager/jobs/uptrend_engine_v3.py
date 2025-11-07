"""
⚠️ DEPRECATED - Kept for reference during v4 implementation only
This file will be archived after v4 is fully implemented and tested.

Replaced by: uptrend_engine_v4.py
"""

from __future__ import annotations

import logging
import math
import os
import statistics as stats
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Global constants (aligned with EMA_Phase_Spec_v1.md)
class Constants:
    """Centralized constants for uptrend engine v3."""
    # ADX floor (for TI/TS and OX/DX)
    ADX_FLOOR = 18.0
    
    # TI/TS thresholds (TS is primary gate, TI reduced for breakout/retest entry)
    TI_ENTRY_THRESHOLD = 0.45  # Reduced - we monitor but TS is primary
    TS_ENTRY_THRESHOLD = 0.58   # Primary gate for S2 entry
    
    # OX/DX thresholds (normal aggressiveness A=0.5)
    DX_BUY_THRESHOLD = 0.65
    OX_SELL_THRESHOLD = 0.65
    
    # Sigmoid scales (for OX/DX/EDX - reuse from v2)
    S1_CURVATURE_K = 0.0008
    S3_RAIL_FAST_K = 1.5
    S3_RAIL_MID_K = 2.0
    S3_RAIL_144_K = 1.5
    S3_RAIL_250_K = 2.0
    S3_EXP_FAST_K = 0.0015
    S3_EXP_MID_K = 0.0010
    S3_RSI_K = 0.5
    S3_ADX_K = 0.3
    S3_EDX_SLOW_K = 0.00025
    S3_EDX_SLOW_333_K = 0.0002
    
    # S1: Simplified - no persistence needed (flip-flopping expected)
    # S2 removed - buy directly from S1
    
    # BUY signal entry zone: use halo (1.0 * ATR)
    S2_SUPPORT_PERSISTENCE_BARS = 3  # Last 3 bars for pre-entry support check (for TS computation)


class UptrendEngineV3:
    """Uptrend Engine v3 - EMA Phase System.
    
    Responsibilities:
    - Detect state using EMA hierarchy + tri-window acceleration
    - Compute TI/TS scores for entry quality gates
    - Compute OX/DX/EDX scores for S3 regime management
    - Emit signals and flags (does NOT make trading decisions)
    - Write live snapshot to features.uptrend_engine_v3
    
    Architecture: Engine emits signals; Portfolio Manager/Backtester makes decisions.
    """

    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)

    # --------------- Data access helpers ---------------
    def _active_positions(self) -> List[Dict[str, Any]]:
        res = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,features")
            .eq("status", "active")
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _write_features(self, pid: Any, features: Dict[str, Any]) -> None:
        self.sb.table("lowcap_positions").update({"features": features}).eq("id", pid).execute()

    def _emit_event(self, event: str, payload: Dict[str, Any]) -> None:
        try:
            contract = str(payload.get("token_contract") or "")
            chain = str(payload.get("chain") or "")
            ts = str(payload.get("ts") or _now_iso())
            state = str((payload.get("payload") or {}).get("state") or (payload.get("state") or ""))
            full_payload = payload.get("payload") or payload
            self.sb.table("uptrend_state_events").insert({
                "token_contract": contract,
                "chain": chain,
                "event_type": event,
                "ts": ts,
                "state": state,
                "payload": full_payload,
            }).execute()
        except Exception:
            pass

    def _append_scores_log(self, contract: str, chain: str, state: str, scores: Dict[str, Any]) -> None:
        try:
            self.sb.table("uptrend_scores_log").insert({
                "token_contract": contract,
                "chain": chain,
                "ts": _now_iso(),
                "state": state,
                "scores": scores,
            }).execute()
        except Exception:
            pass

    # --------------- TA/EMA readers ---------------
    def _read_ta(self, features: Dict[str, Any]) -> Dict[str, Any]:
        return features.get("ta") or {}
    
    def _read_sr_levels(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Read S/R levels from geometry (used for exits and optional entry boost)."""
        geom = features.get("geometry") or {}
        levels = ((geom.get("levels") or {}).get("sr_levels") or [])
        return list(levels)

    def _get_ema_values(self, ta: Dict[str, Any]) -> Dict[str, float]:
        """Extract EMA values from TA block."""
        ema = ta.get("ema") or {}
        return {
            "ema20": float(ema.get("ema20_1h") or 0.0),
            "ema30": float(ema.get("ema30_1h") or 0.0),
            "ema60": float(ema.get("ema60_1h") or 0.0),
            "ema144": float(ema.get("ema144_1h") or 0.0),
            "ema250": float(ema.get("ema250_1h") or 0.0),
            "ema333": float(ema.get("ema333_1h") or 0.0),
        }

    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
        """Get latest close price (bar close for deterministic checks)."""
        row = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, low_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if row:
            r = row[0]
            return {
                "ts": str(r.get("timestamp")),
                "close": float(r.get("close_native") or 0.0),
                "low": float(r.get("low_native") or 0.0),
            }
        return {"ts": None, "close": 0.0, "low": 0.0}

    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 400) -> List[Dict[str, Any]]:
        """Fetch recent OHLC bars (needed for tri-window acceleration and other calculations)."""
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        rows.reverse()
        return rows

    def _fetch_ohlc_since(self, contract: str, chain: str, since_iso: str) -> List[Dict[str, Any]]:
        """Fetch OHLC bars since a timestamp."""
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .gte("timestamp", since_iso)
            .order("timestamp", desc=False)
            .limit(300)
            .execute()
            .data
            or []
        )
        return rows

    # --------------- Tri-Window Acceleration ---------------
    def _compute_tri_window_acceleration(self, ema_series: List[float], n: int) -> Dict[str, Any]:
        """Compute tri-window acceleration for an EMA(n) series.
        
        Returns acceleration classification with S_micro, S_meso, S_base slopes.
        """
        if len(ema_series) < 2:
            return {"accelerating_up": False, "accelerating_down": False, "rolling_over": False,
                    "bottoming": False, "steady_up": False, "steady": False,
                    "s_micro": 0.0, "s_meso": 0.0, "s_base": 0.0}
        
        # Compute slopes
        slopes: List[float] = []
        for i in range(1, len(ema_series)):
            if ema_series[i] is not None and ema_series[i-1] is not None:
                slopes.append(ema_series[i] - ema_series[i-1])
            else:
                slopes.append(0.0)
        
        if not slopes:
            return {"accelerating_up": False, "accelerating_down": False, "rolling_over": False,
                    "bottoming": False, "steady_up": False, "steady": False,
                    "s_micro": 0.0, "s_meso": 0.0, "s_base": 0.0}
        
        # Window sizes (proportional to EMA length n)
        W_micro = max(5, round(n / 15))
        W_meso = max(10, round(n / 5))
        W_base = max(20, round(n / 2))
        
        # Need enough data
        required_len = max(W_micro, W_meso, W_base)
        if len(slopes) < required_len:
            return {"accelerating_up": False, "accelerating_down": False, "rolling_over": False,
                    "bottoming": False, "steady_up": False, "steady": False,
                    "s_micro": 0.0, "s_meso": 0.0, "s_base": 0.0}
        
        # Compute average slopes over windows (from most recent)
        recent_slopes = slopes[-required_len:]
        S_micro = stats.fmean(recent_slopes[-W_micro:]) if recent_slopes[-W_micro:] else 0.0
        S_meso = stats.fmean(recent_slopes[-W_meso:]) if recent_slopes[-W_meso:] else 0.0
        S_base = stats.fmean(recent_slopes[-W_base:]) if recent_slopes[-W_base:] else 0.0
        
        # Noise band: stdev over W_meso window
        meso_window_slopes = recent_slopes[-W_meso:] if len(recent_slopes) >= W_meso else recent_slopes
        slope_stdev = stats.pstdev(meso_window_slopes) if len(meso_window_slopes) > 1 else 1.0
        noise_band = slope_stdev * 0.2
        
        # Comparison functions
        def gt(a: float, b: float) -> bool:
            return (a - b) > noise_band
        
        def lt(a: float, b: float) -> bool:
            return (b - a) > noise_band
        
        def approx(a: float, b: float) -> bool:
            return abs(a - b) <= noise_band
        
        # Classifications
        accelerating_up = gt(S_micro, S_meso) and gt(S_meso, S_base) and gt(S_base, 0.0) and (S_meso >= 0.0)
        accelerating_down = lt(S_micro, S_meso) and lt(S_meso, S_base) and lt(S_base, 0.0) and (S_meso <= 0.0)
        rolling_over = lt(S_micro, S_meso) and gt(S_meso, S_base)
        bottoming = gt(S_micro, S_meso) and lt(S_meso, S_base)
        steady_up = approx(S_micro, S_meso) and gt(S_micro, S_base) and gt(S_meso, S_base) and (S_micro >= 0.0) and (S_meso >= 0.0)
        steady = approx(S_micro, S_meso) and approx(S_meso, S_base)
        
        return {
            "accelerating_up": accelerating_up,
            "accelerating_down": accelerating_down,
            "rolling_over": rolling_over,
            "bottoming": bottoming,
            "steady_up": steady_up,
            "steady": steady,
            "s_micro": S_micro,
            "s_meso": S_meso,
            "s_base": S_base,
        }

    def _build_ema_series_from_ohlc(self, contract: str, chain: str, ema_length: int) -> List[float]:
        """Build EMA series from OHLC data for tri-window acceleration.
        
        Note: Matches ta_tracker.py's EMA calculation for consistency.
        ta_tracker provides latest EMA values in ta.features, but we need full series
        for tri-window acceleration, so we recompute from OHLC here.
        """
        rows = self._fetch_recent_ohlc(contract, chain, limit=max(400, ema_length * 2))
        if not rows:
            return []
        
        closes = [float(r.get("close_native") or 0.0) for r in rows if float(r.get("close_native") or 0.0) > 0]
        if not closes:
            return []
        
        # Match ta_tracker.py's EMA initialization (starts with first value, not SMA)
        # This ensures consistency with stored EMA values in ta.features
        alpha = 2.0 / (ema_length + 1.0)
        ema_values: List[float] = [closes[0]]
        
        # Compute EMA for remaining values (matches ta_tracker._ema_series exactly)
        for v in closes[1:]:
            ema_new = alpha * v + (1.0 - alpha) * ema_values[-1]
            ema_values.append(ema_new)
        
        return ema_values

    # --------------- EMA Hierarchy Checks ---------------
    def _check_s0_order(self, ema_vals: Dict[str, float]) -> bool:
        """Check if EMAs are in perfect bearish order (band-based).
        
        Band (20/30) below mid and slow descending: 60 < 144 < 250 < 333.
        No requirement on 20 vs 30 ordering.
        """
        return (
            ema_vals["ema20"] < ema_vals["ema60"] and
            ema_vals["ema30"] < ema_vals["ema60"] and
            ema_vals["ema60"] < ema_vals["ema144"] < ema_vals["ema250"] < ema_vals["ema333"]
        )

    def _check_bullish_alignment_band(self, ema_vals: Dict[str, float]) -> bool:
        """Check full bullish alignment (band-based) for S2→S3.
        
        Band (20/30) above mid and slow ascending: 60 > 144 > 250 > 333.
        No requirement on 20 vs 30 ordering.
        """
        return (
            ema_vals["ema20"] > ema_vals["ema60"] and
            ema_vals["ema30"] > ema_vals["ema60"] and
            ema_vals["ema60"] > ema_vals["ema144"] > ema_vals["ema250"] > ema_vals["ema333"]
        )

    def _check_s3_order(self, ema_vals: Dict[str, float]) -> bool:
        """Check if all EMAs are above EMA333 (S3)."""
        return (
            ema_vals["ema20"] > ema_vals["ema333"] and
            ema_vals["ema30"] > ema_vals["ema333"] and
            ema_vals["ema60"] > ema_vals["ema333"] and
            ema_vals["ema144"] > ema_vals["ema333"] and
            ema_vals["ema250"] > ema_vals["ema333"]
        )

    def _check_fast_band_above_60(self, ema_vals: Dict[str, float]) -> bool:
        """Check if both EMA20 and EMA30 are above EMA60."""
        return ema_vals["ema20"] > ema_vals["ema60"] and ema_vals["ema30"] > ema_vals["ema60"]

    def _check_fast_band_below_60(self, ema_vals: Dict[str, float]) -> bool:
        """Check if both EMA20 and EMA30 are below EMA60."""
        return ema_vals["ema20"] < ema_vals["ema60"] and ema_vals["ema30"] < ema_vals["ema60"]
    
    def _check_fast_band_at_bottom(self, ema_vals: Dict[str, float]) -> bool:
        """Check if both EMA20 and EMA30 are below all other EMAs (fast band at bottom).
        
        Treats EMA20/30 as a band - both must be below the current lowest support EMA
        among EMA60, EMA144, EMA250, EMA333. Order between EMA20/30 doesn't matter.
        """
        lowest_support = min(
            ema_vals["ema60"],
            ema_vals["ema144"],
            ema_vals["ema250"],
            ema_vals["ema333"],
        )
        return ema_vals["ema20"] < lowest_support and ema_vals["ema30"] < lowest_support

    # --------------- S1 Acceleration Detection (with persistence) ---------------
    def _detect_s1_acceleration(self, contract: str, chain: str, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Detect S1 acceleration pattern (S1.A or S1.B) with persistence tracking.
        
        Returns None if not valid, or dict with acceleration type and slopes.
        """
        ta = self._read_ta(features)
        if not ta:
            return None
        
        # Build EMA60 series for tri-window acceleration
        ema60_series = self._build_ema_series_from_ohlc(contract, chain, 60)
        if len(ema60_series) < 30:  # Need at least base window
            return None
        
        accel = self._compute_tri_window_acceleration(ema60_series, 60)
        
        # Check for S1.A (Accelerating Up) or S1.B (Steady Lift)
        s1_type = None
        if accel["accelerating_up"]:
            s1_type = "accelerating_up"
        elif accel["steady_up"]:
            s1_type = "steady_lift"
        else:
            return None
        
        # Check persistence in meta
        meta = dict(features.get("uptrend_engine_v3_meta") or {})
        s1_meta = dict(meta.get("s1") or {})
        
        # Track persistence count
        last_type = str(s1_meta.get("acceleration_type") or "")
        if last_type == s1_type:
            persistence_count = int(s1_meta.get("acceleration_persistence", 0)) + 1
        else:
            persistence_count = 1
        
        # Update meta
        s1_meta.update({
            "acceleration_type": s1_type,
            "acceleration_persistence": persistence_count,
            "s_micro": accel["s_micro"],
            "s_meso": accel["s_meso"],
            "s_base": accel["s_base"],
        })
        meta["s1"] = s1_meta
        features["uptrend_engine_v3_meta"] = meta
        
        # Require 3-bar persistence
        if persistence_count >= Constants.S1_ACCELERATION_PERSISTENCE_BARS:
            return {
                "type": s1_type,
                "s_micro": accel["s_micro"],
                "s_meso": accel["s_meso"],
                "s_base": accel["s_base"],
                "valid": True,
            }
        
        return {
            "type": s1_type,
            "s_micro": accel["s_micro"],
            "s_meso": accel["s_meso"],
            "s_base": accel["s_base"],
            "valid": False,  # Not yet persisted
        }

    def _check_s1_cancel(self, contract: str, chain: str, features: Dict[str, Any], ema_vals: Dict[str, float]) -> Tuple[bool, str]:
        """Check if S1 should be canceled (rolling over or fast band drops).
        
        Returns (should_cancel, reason) with persistence tracking.
        """
        meta = dict(features.get("uptrend_engine_v3_meta") or {})
        s1_meta = dict(meta.get("s1") or {})
        
        # Check rolling over condition
        ema60_series = self._build_ema_series_from_ohlc(contract, chain, 60)
        if len(ema60_series) >= 30:
            accel = self._compute_tri_window_acceleration(ema60_series, 60)
            rolling_over = (
                accel["rolling_over"] and
                accel["s_meso"] <= 0.0 and
                accel["s_micro"] < 0.0
            )
            
            if rolling_over:
                cancel_count = int(s1_meta.get("rolling_over_persistence", 0)) + 1
                s1_meta["rolling_over_persistence"] = cancel_count
                if cancel_count >= Constants.S1_CANCEL_PERSISTENCE_BARS:
                    return (True, "rolling_over")
            else:
                s1_meta["rolling_over_persistence"] = 0
        
        # Check fast band drops condition
        fast_band_below = self._check_fast_band_below_60(ema_vals)
        if fast_band_below:
            cancel_count = int(s1_meta.get("fast_band_drop_persistence", 0)) + 1
            s1_meta["fast_band_drop_persistence"] = cancel_count
            if cancel_count >= Constants.S1_CANCEL_PERSISTENCE_BARS:
                return (True, "fast_band_drop")
        else:
            s1_meta["fast_band_drop_persistence"] = 0
        
        meta["s1"] = s1_meta
        features["uptrend_engine_v3_meta"] = meta
        
        return (False, "")

    # --------------- S2 Entry Detection ---------------
    def _check_buy_signal_conditions(self, contract: str, chain: str, features: Dict[str, Any], ema_vals: Dict[str, float], price: float) -> Dict[str, Any]:
        """Check if BUY signal conditions are met (directly from S1, no S2 state).
        
        Returns dict with entry_ready flag and details.
        
        Note: We're already in S1, so fast_above_60 and price_above_60 are not checked here.
        Only need: entry_zone, slope_ok, and ts_ok.
        """
        ta = self._read_ta(features)
        slopes = ta.get("ema_slopes") or {}
        
        # Condition 1: Entry zone (within halo = 1.0 * ATR of EMA60)
        entry_zone = False
        atr = ta.get("atr") or {}
        atr_1h = float(atr.get("atr_1h") or 0.0)
        if ema_vals["ema60"] > 0 and atr_1h > 0:
            halo = 1.0 * atr_1h
            entry_zone = abs(price - ema_vals["ema60"]) <= halo
        
        # Condition 2: Slope requirement
        # Use TA tracker slopes (already rolling from before S1, computed continuously)
        # ta_tracker computes: 10-bar linear regression, normalized as %/bar
        ema60_slope_ta = float(slopes.get("ema60_slope") or 0.0)
        ema144_slope_ta = float(slopes.get("ema144_slope") or 0.0)
        
        # Slope condition: EMA60 rising OR EMA144 flat/rising
        slope_ok = (ema60_slope_ta > 0.0) or (ema144_slope_ta >= 0.0)
        
        # Condition 3: TS gate only (TI removed - too slow)
        # Use TS with S/R boost if available, otherwise base TS
        ti_ts = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
        ts_with_boost = ti_ts.get("trend_strength_with_boost", ti_ts["trend_strength"])
        ts_ok = ts_with_boost >= Constants.TS_ENTRY_THRESHOLD
        
        entry_ready = (
            entry_zone and
            slope_ok and
            ts_ok
        )
        
        # Store TA slopes for diagnostics (from ta_tracker, already rolling from before S1)
        return {
            "entry_ready": entry_ready,
            "entry_zone": entry_zone,
            "slope_ok": slope_ok,
            "ts_ok": ts_ok,
            "ts_score": ti_ts["trend_strength"],
            "ts_with_boost": ti_ts.get("trend_strength_with_boost", ti_ts["trend_strength"]),  # TS with S/R boost
            "ema60_value": ema_vals["ema60"],
            "ema60_meso_slope": ema60_slope_ta,  # From TA tracker (10-bar %/bar)
            "ema144_meso_slope": ema144_slope_ta,  # From TA tracker (10-bar %/bar)
        }

    def _get_ema60_meso_slope(self, contract: str, chain: str, features: Dict[str, Any]) -> float:
        """Get EMA60 meso slope for S2 entry check."""
        ema60_series = self._build_ema_series_from_ohlc(contract, chain, 60)
        if len(ema60_series) < 12:  # Need at least meso window
            return 0.0
        accel = self._compute_tri_window_acceleration(ema60_series, 60)
        return accel["s_meso"]

    def _get_ema144_meso_slope(self, contract: str, chain: str, features: Dict[str, Any]) -> float:
        """Get EMA144 meso slope for S2 entry check."""
        ema144_series = self._build_ema_series_from_ohlc(contract, chain, 144)
        if len(ema144_series) < 30:  # Need at least meso window
            return 0.0
        accel = self._compute_tri_window_acceleration(ema144_series, 144)
        return accel["s_meso"]

    # --------------- TI/TS Computation (with EMA60 Support Persistence) ---------------
    def _compute_support_persistence_ema60(self, contract: str, chain: str, features: Dict[str, Any], ema60: float, atr_1h: float) -> float:
        """Compute support persistence relative to EMA60 (last 3 bars, pre-entry check).
        
        Same formula as v2 but tracks EMA60 instead of S/R level.
        """
        if ema60 <= 0.0 or atr_1h <= 0.0:
            return 0.0
        
        # Fetch last 3 bars (breakout/retest context)
        rows = self._fetch_recent_ohlc(contract, chain, limit=3)
        if len(rows) < 3:
            return 0.0
        
        closes = [float(r.get("close_native") or 0.0) for r in rows[-3:]]
        lows = [float(r.get("low_native") or 0.0) for r in rows[-3:]]
        highs = [float(r.get("high_native") or 0.0) for r in rows[-3:]]
        
        # Halo around EMA60
        halo = 0.5 * atr_1h
        
        # Close persistence: % of closes above EMA60
        cnt_closes = sum(1 for v in closes if v >= ema60)
        close_persistence = 1.0 - math.exp(-(cnt_closes / 6.0))
        
        # Absorption wicks: wicks below EMA60 with closes above
        wick_cnt = sum(1 for lo, cl in zip(lows, closes) if lo < ema60 and cl >= ema60)
        absorption_wicks = 1.0 - math.exp(-(wick_cnt / 2.0))
        
        # Reaction quality: bounce off EMA60 (max high - EMA60 in ATR terms)
        if highs:
            bounce_atr = (max(highs) - ema60) / max(atr_1h, 1e-9)
            reaction_quality = min(1.0, bounce_atr / 1.0)
        else:
            reaction_quality = 0.0
        
        # Touch confirm: current close within halo and above EMA60
        current_close = closes[-1] if closes else 0.0
        current_low = lows[-1] if lows else 0.0
        touch_confirm = 1.0 if (current_low <= ema60 + halo and current_close >= ema60) else 0.0
        
        # Same weights as v2
        support_persistence = 0.25 * touch_confirm + 0.20 * reaction_quality + 0.40 * close_persistence + 0.15 * absorption_wicks
        
        return max(0.0, min(1.0, support_persistence))
    
    def _compute_ti_ts_s2(self, contract: str, chain: str, features: Dict[str, Any], ema_vals: Dict[str, float]) -> Dict[str, float]:
        """Compute Trend Integrity and Trend Strength for S2 entry.
        
        Includes EMA60-based support persistence (pre-entry, last 3 bars).
        TS is primary gate, TI is monitored but lower threshold.
        """
        ta = self._read_ta(features)
        slopes = ta.get("ema_slopes") or {}
        mom = ta.get("momentum") or {}
        atr = ta.get("atr") or {}
        
        def _clip01(x: float) -> float:
            return max(0.0, min(1.0, x))
        
        # Support persistence (EMA60-based, last 3 bars)
        ema60 = ema_vals["ema60"]
        atr_1h = float(atr.get("atr_1h") or 0.0)
        support_persistence = self._compute_support_persistence_ema60(contract, chain, features, ema60, atr_1h)
        
        # EMA alignment score
        ema60_slope = float(slopes.get("ema60_slope") or 0.0)
        ema144_slope = float(slopes.get("ema144_slope") or 0.0)
        ema250_slope = float(slopes.get("ema250_slope") or 0.0)
        ema333_slope = float(slopes.get("ema333_slope") or 0.0)
        d_ema144_slope = float(slopes.get("d_ema144_slope") or 0.0)
        d_ema250_slope = float(slopes.get("d_ema250_slope") or 0.0)
        d_ema333_slope = float(slopes.get("d_ema333_slope") or 0.0)
        
        # Slow positive count
        slow_pos_count = sum(1 for s in [ema144_slope, ema250_slope, ema333_slope] if s >= 0.0)
        slow_positive = slow_pos_count / 3.0
        
        # Slow acceleration
        slow_accel = sum(1.0 for s in [d_ema144_slope, d_ema250_slope, d_ema333_slope] if s > 0.0) / 3.0
        
        # Mid help
        mid_help = 1.0 if ema60_slope >= 0.0 else 0.0
        
        # Fast > mid ordering
        fast_gt_mid = 1.0 if ema_vals["ema20"] > ema_vals["ema60"] else 0.0
        
        # Separations
        sep_fast = float((ta.get("separations") or {}).get("sep_fast") or 0.0)
        
        # EMA alignment composite
        ema_alignment = (
            0.50 * _clip01(0.30 * slow_positive + 0.40 * slow_accel + 0.30 * slow_positive) +
            0.15 * mid_help +
            0.20 * fast_gt_mid +
            0.15 * _clip01(sep_fast)
        )
        
        # Volatility coherence
        atr_mean_20 = float(atr.get("atr_mean_20") or atr_1h)
        red_ratio = (atr_1h - atr_mean_20) / max(atr_mean_20, 1e-9)
        volatility_coherence = 1.0 / (1.0 + math.exp(red_ratio / 0.3))
        
        # TI (kept for reference but not used in entry decision)
        trend_integrity = 0.55 * support_persistence + 0.35 * ema_alignment + 0.10 * volatility_coherence
        
        # TS (momentum-based, primary gate)
        rsi_slope_10 = float(mom.get("rsi_slope_10") or 0.0)
        adx_level = float(mom.get("adx_1h") or 0.0)
        adx_slope_10 = float(mom.get("adx_slope_10") or 0.0)
        
        def sigmoid(x: float, k: float) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        rsi_term = sigmoid(rsi_slope_10, Constants.S3_RSI_K)
        adx_term = sigmoid(adx_slope_10, Constants.S3_ADX_K) if adx_level >= Constants.ADX_FLOOR else 0.0
        trend_strength = 0.6 * rsi_term + 0.4 * adx_term
        
        # Optional S/R boost: if S/R level near EMA60, boost TS by up to +0.15 (not required)
        trend_strength_with_boost = trend_strength
        sr_levels = self._read_sr_levels(features)
        if sr_levels and ema60 > 0 and atr_1h > 0:
            halo = 1.0 * atr_1h  # Same halo as entry zone
            for sr in sr_levels[:10]:  # Check top 10 S/R levels
                try:
                    sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                    if sr_price > 0:
                        distance = abs(sr_price - ema60)
                        if distance <= halo:
                            # S/R level near EMA60 - boost TS (not required, optional)
                            sr_strength = float(sr.get("strength", 10) or 10)
                            # Normalize strength (0-20 scale) and apply boost up to +0.15
                            boost = min(0.15, (sr_strength / 20.0) * 0.15)
                            trend_strength_with_boost = min(1.0, trend_strength + boost)
                            break  # Use first matching level
                except Exception:
                    pass
        
        return {
            "trend_integrity": _clip01(trend_integrity),  # Kept for reference
            "trend_strength": _clip01(trend_strength),
            "trend_strength_with_boost": _clip01(trend_strength_with_boost),  # TS with optional S/R boost
        }

    # --------------- S3 OX/DX/EDX Computation (Reuse from v2) ---------------
    def _compute_s3_scores(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Compute OX/DX/EDX scores for S3 regime. Reuses logic from v2."""
        # Import the v2 method or copy the logic
        # For now, we'll copy the core logic from v2
        ta = self._read_ta(features)
        ema = ta.get("ema") or {}
        sep = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        mom = ta.get("momentum") or {}
        vol = ta.get("volume") or {}
        slopes = ta.get("ema_slopes") or {}
        
        last = self._latest_close_1h(contract, chain)
        px = last["close"]
        atr_1h = float(atr.get("atr_1h") or 0.0)
        atr_mean_20 = float(atr.get("atr_mean_20") or (atr_1h if atr_1h else 1.0))
        ema20 = float(ema.get("ema20_1h") or 0.0)
        ema60 = float(ema.get("ema60_1h") or 0.0)
        ema144 = float(ema.get("ema144_1h") or 0.0)
        ema250 = float(ema.get("ema250_1h") or 0.0)
        ema333 = float(ema.get("ema333_1h") or 0.0)
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        vo_z_1h = float(vol.get("vo_z_1h") or 0.0)
        ema20_slope = float(slopes.get("ema20_slope") or 0.0)
        d_ema144_slope = float(slopes.get("d_ema144_slope") or 0.0)
        
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        # EDX computation (same as v2)
        ema144_slope = float(slopes.get("ema144_slope") or 0.0)
        ema250_slope = float(slopes.get("ema250_slope") or 0.0)
        ema333_slope = float(slopes.get("ema333_slope") or 0.0)
        slow_down = sigmoid(-ema250_slope / Constants.S3_EDX_SLOW_K, 1.0) * 0.5 + sigmoid(-ema333_slope / Constants.S3_EDX_SLOW_333_K, 1.0) * 0.5
        
        # Structure failure
        rows = self._fetch_recent_ohlc(contract, chain, limit=50)
        closes = [float(r.get("close_native") or 0.0) for r in rows]
        lows = [float(r.get("low_native") or 0.0) for r in rows]
        below_mid_ratio = 0.0
        if ema60 > 0.0 and closes:
            below_mid_ratio = sum(1 for c in closes if c < ema60) / float(len(closes) or 1)
        ll_ratio = 0.0
        if len(lows) >= 2:
            ll_ratio = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i - 1]) / float(len(lows) - 1)
        struct = 0.5 * sigmoid((ll_ratio - 0.5) / 0.2, 1.0) + 0.5 * sigmoid((below_mid_ratio - 0.4) / 0.2, 1.0)
        
        # Participation decay
        part_decay = sigmoid(-vo_z_1h / 1.0, 1.0)
        
        # Volatility disorder
        trs: List[float] = []
        ups: List[float] = []
        downs: List[float] = []
        prev_close = None
        for r in rows:
            h = float(r.get("high_native") or 0.0)
            l = float(r.get("low_native") or 0.0)
            c = float(r.get("close_native") or 0.0)
            if prev_close is None:
                prev_close = c
                continue
            tr = max(h - l, abs(h - prev_close), abs(prev_close - l))
            trs.append(tr)
            if c >= prev_close:
                ups.append(tr)
            else:
                downs.append(tr)
            prev_close = c
        
        up_avg = stats.fmean(ups) if ups else (sum(trs) / len(trs) if trs else 0.0)
        down_avg = stats.fmean(downs) if downs else (sum(trs) / len(trs) if trs else 0.0)
        asym = 0.0
        if up_avg > 0.0:
            asym = sigmoid(((down_avg / up_avg) - 1.0) / 0.2, 1.0)
        
        # Geometry rollover
        geom_roll = 0.6 * sigmoid(-dsep_mid / Constants.S3_EXP_MID_K, 1.0) + 0.4 * sigmoid(-dsep_fast / Constants.S3_EXP_FAST_K, 1.0)
        
        # EDX composite
        edx_raw = 0.30 * slow_down + 0.25 * struct + 0.20 * part_decay + 0.15 * asym + 0.10 * geom_roll
        edx_raw = max(0.0, min(1.0, edx_raw))
        
        # Smooth EDX with EMA
        meta = dict(features.get("uptrend_engine_v3_meta") or {})
        s3meta = dict(meta.get("s3") or {})
        alpha = 2.0 / (20.0 + 1.0)
        asset_key = f"{chain}:{contract}"
        last_asset_key = s3meta.get("asset_key")
        prev_edx = float(s3meta.get("edx_ema") or edx_raw)
        if last_asset_key and last_asset_key != asset_key:
            prev_edx = edx_raw
        edx = alpha * edx_raw + (1.0 - alpha) * prev_edx
        s3meta["edx_ema"] = edx
        s3meta["asset_key"] = asset_key
        meta["s3"] = s3meta
        features["uptrend_engine_v3_meta"] = meta
        
        # OX computation
        rail_fast = sigmoid((px - ema20) / max(atr_1h * Constants.S3_RAIL_FAST_K, 1e-9), 1.0) if atr_1h > 0 else 0.0
        rail_mid = sigmoid((px - ema60) / max(atr_1h * Constants.S3_RAIL_MID_K, 1e-9), 1.0) if atr_1h > 0 else 0.0
        rail_144 = sigmoid((px - ema144) / max(atr_1h * Constants.S3_RAIL_144_K, 1e-9), 1.0) if atr_1h > 0 else 0.0
        rail_250 = sigmoid((px - ema250) / max(atr_1h * Constants.S3_RAIL_250_K, 1e-9), 1.0) if atr_1h > 0 else 0.0
        exp_fast = sigmoid(dsep_fast / Constants.S3_EXP_FAST_K, 1.0)
        exp_mid = sigmoid(dsep_mid / Constants.S3_EXP_MID_K, 1.0)
        atr_surge = sigmoid((atr_1h / max(atr_mean_20, 1e-9)) - 1.0, 1.0)
        fragility = sigmoid(-ema20_slope / Constants.S1_CURVATURE_K, 1.0)
        ox_base = (
            0.35 * rail_fast + 0.20 * rail_mid + 0.10 * rail_144 + 0.10 * rail_250 +
            0.10 * exp_fast + 0.05 * exp_mid + 0.05 * atr_surge + 0.05 * fragility
        )
        edx_boost = max(0.0, min(0.5, edx - 0.5))
        ox = max(0.0, min(1.0, ox_base * (1.0 + 0.33 * edx_boost)))
        
        # DX computation
        if ema333 > ema144 and (ema333 - ema144) > 0 and px > 0:
            x = max(0.0, min(1.0, (px - ema144) / max((ema333 - ema144), 1e-9)))
        else:
            x = 1.0 if px <= ema144 else 0.0
        
        band_width = max(ema333 - ema144, 1e-9)
        comp_mult = sigmoid((0.03 - (band_width / max(px, 1e-9))) / 0.02, 1.0)
        dx_location = math.exp(-3.0 * x) * (1.0 + 0.3 * comp_mult)
        exhaustion = max(0.0, min(1.0, sigmoid(-vo_z_1h / 1.0, 1.0)))
        atr_relief = sigmoid(((atr_1h / max(atr_mean_20, 1e-9)) - 0.9) / 0.05, 1.0)
        rsi_slope_10 = float(mom.get("rsi_slope_10") or 0.0)
        adx_level = float(mom.get("adx_1h") or 0.0)
        adx_slope_10 = float(mom.get("adx_slope_10") or 0.0)
        rsi_relief = sigmoid(rsi_slope_10 / Constants.S3_RSI_K, 1.0)
        adx_relief = sigmoid(adx_slope_10 / Constants.S3_ADX_K, 1.0) if adx_level >= Constants.ADX_FLOOR else 0.0
        mom_relief = 0.5 * rsi_relief + 0.5 * adx_relief
        relief = 0.5 * atr_relief + 0.5 * mom_relief
        curl = 1.0 if d_ema144_slope > 0.0 else 0.0
        dx_base = 0.45 * dx_location + 0.25 * exhaustion + 0.25 * relief + 0.05 * curl
        supp = max(0.0, min(0.4, edx - 0.6))
        dx = max(0.0, min(1.0, dx_base * (1.0 - 0.5 * supp)))
        
        return {
            "scores": {"ox": ox, "dx": dx, "edx": edx},
            "flags": {"dx_flag": bool(px <= ema144)},
            "diagnostics": {
                "rail_fast": rail_fast,
                "rail_mid": rail_mid,
                "rail_144": rail_144,
                "rail_250": rail_250,
                "exp_fast": exp_fast,
                "exp_mid": exp_mid,
                "atr_surge": atr_surge,
                "fragility": fragility,
                "dx_location": dx_location,
                "exhaustion": exhaustion,
                "relief": relief,
                "edx_raw": edx_raw,
                "edx_slow": slow_down,
                "edx_struct": struct,
                "edx_part": part_decay,
                "edx_vol_dis": asym,
                "edx_geom": geom_roll,
            },
            "features": features,
        }

    # --------------- Payload Builder ---------------
    def _build_payload(self, state: str, features: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        """Build unified payload for state emission."""
        ta = self._read_ta(features)
        ema = ta.get("ema") or {}
        
        payload: Dict[str, Any] = {
            "state": state,
            "timeframe": "1h",
            "t0": _now_iso(),
            "flag": extra.get("flag", {}),
            "flags": extra.get("flags", {}),
            "scores": extra.get("scores", {}),
            "levels": {
                "ema20": float(ema.get("ema20_1h") or 0.0),
                "ema30": float(ema.get("ema30_1h") or 0.0),
                "ema60": float(ema.get("ema60_1h") or 0.0),
                "ema144": float(ema.get("ema144_1h") or 0.0),
                "ema250": float(ema.get("ema250_1h") or 0.0),
                "ema333": float(ema.get("ema333_1h") or 0.0),
            },
            "diagnostics": extra.get("diagnostics", {}),
            "meta": {"updated_at": _now_iso()},
        }
        
        return payload

    # --------------- Main State Machine Loop ---------------
    def run(self) -> int:
        """Main loop: process all active positions and emit state signals."""
        now = datetime.now(timezone.utc)
        updated = 0
        positions = self._active_positions()
        
        for p in positions:
            try:
                pid = p.get("id")
                contract = p.get("token_contract")
                chain = p.get("token_chain")
                features = p.get("features") or {}
                prev_payload = dict(features.get("uptrend_engine_v3") or {})
                prev_state = str(prev_payload.get("state") or "")
                
                ta = self._read_ta(features)
                if not ta:
                    continue
                
                ema_vals = self._get_ema_values(ta)
                last = self._latest_close_1h(contract, chain)
                price = last["close"]
                
                if price <= 0:
                    continue
                
                # Bootstrap: If no previous state, determine initial state
                if not prev_state or prev_state == "":
                    # Bootstrap logic: check if all EMAs above 333 (S3) or perfect order (S0)
                    if self._check_s3_order(ema_vals):
                        # Bootstrap to S3
                        s3_scores = self._compute_s3_scores(contract, chain, features)
                        ti_ts = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                        payload = self._build_payload("S3", features, {
                            "flags": {
                                "trending": True,
                                "dx_flag": s3_scores["flags"]["dx_flag"],
                                "emergency_exit": {"active": False},
                            },
                            "scores": {
                                **s3_scores["scores"],
                                "ti": ti_ts["trend_integrity"],
                                "ts": ti_ts["trend_strength"],
                            },
                            "diagnostics": s3_scores["diagnostics"],
                        })
                        
                        # Add geometry context for S3 exits
                        try:
                            ta_local = self._read_ta(features)
                            atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                            last_px = price
                            halo = max(0.5 * atr_1h, 0.03 * last_px) if last_px > 0 else 0.0
                            
                            sr_levels = self._read_sr_levels(features)
                            flipped_sr = []
                            for sr in sr_levels[:5]:
                                try:
                                    sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                                    if sr_price > 0:
                                        flipped_sr.append({
                                            "level": sr_price,
                                            "score": float(sr.get("strength", 10) or 10)
                                        })
                                except Exception:
                                    pass
                            
                            flipped_sr.sort(key=lambda x: float(x.get("level", 0.0)), reverse=True)
                            base_sr = float(flipped_sr[-1].get("level", 0.0)) if flipped_sr else 0.0
                            
                            payload["sr_context"] = {
                                "halo": halo,
                                "base_sr_level": base_sr,
                                "flipped_sr_levels": flipped_sr,
                            }
                        except Exception:
                            payload["sr_context"] = {}
                        
                        features = s3_scores["features"]
                    else:
                        # Bootstrap to S0
                        payload = self._build_payload("S0", features, {
                            "flag": {"watch_only": True},
                            "scores": {},
                        })
                
                # Determine current state
                if not payload:
                    payload = None
                
                # Global precedence: if fast band is at bottom, exit to S0 immediately
                if not payload and self._check_fast_band_at_bottom(ema_vals):
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "scores": {},
                        "diagnostics": {"s1_exit": True, "reason": "fast_band_at_bottom"},
                    })

                # S0: Perfect bearish order
                if not payload and self._check_s0_order(ema_vals):
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "scores": {},
                    })
                    # Clear any S1/S2 meta when in S0
                    meta = dict(features.get("uptrend_engine_v3_meta") or {})
                    meta.pop("s1", None)
                    meta.pop("s2", None)
                    features["uptrend_engine_v3_meta"] = meta
                
                # S1: Simplified - Fast band above 60 + Price above 60, must come from S0
                elif not payload and self._check_fast_band_above_60(ema_vals) and price > ema_vals["ema60"]:
                    # Must come from S0 (no acceleration patterns, no persistence)
                    if prev_state == "S0" or not prev_state:
                        # First entry to S1 - check buy conditions too
                        buy_check = self._check_buy_signal_conditions(contract, chain, features, ema_vals, price)
                        meta = dict(features.get("uptrend_engine_v3_meta") or {})
                        s1_meta = dict(meta.get("s1") or {})
                        if "ema60_entry" not in s1_meta:
                            s1_meta["ema60_entry"] = ema_vals["ema60"]
                            meta["s1"] = s1_meta
                            features["uptrend_engine_v3_meta"] = meta
                        
                        if buy_check["entry_ready"]:
                            payload = self._build_payload("S1", features, {
                                "flag": {
                                    "s1_valid": True,
                                    "buy_signal": True,
                                    "entry_zone": buy_check["entry_zone"],
                                },
                                "scores": {
                                    "ts": buy_check["ts_score"],
                                    "ts_with_boost": buy_check.get("ts_with_boost", buy_check["ts_score"]),
                                },
                                "levels": {
                                    "base_sr_level": s1_meta.get("ema60_entry", ema_vals["ema60"]),
                                },
                                "diagnostics": {
                                    "buy_check": {
                                        "entry_zone": buy_check.get("entry_zone", False),
                                        "slope_ok": buy_check.get("slope_ok", False),
                                        "ts_ok": buy_check.get("ts_ok", False),
                                        "ema60_slope": buy_check.get("ema60_meso_slope", 0.0),
                                        "ema144_slope": buy_check.get("ema144_meso_slope", 0.0),
                                    },
                                },
                            })
                        else:
                            payload = self._build_payload("S1", features, {
                                "flag": {"s1_valid": True},
                                "scores": {
                                    "ts": buy_check.get("ts_score", 0.0),
                                    "ts_with_boost": buy_check.get("ts_with_boost", buy_check.get("ts_score", 0.0)),
                                },
                                "diagnostics": {
                                    "buy_check": {
                                        "entry_zone": buy_check.get("entry_zone", False),
                                        "slope_ok": buy_check.get("slope_ok", False),
                                        "ts_ok": buy_check.get("ts_ok", False),
                                        "ema60_slope": buy_check.get("ema60_meso_slope", 0.0),
                                        "ema144_slope": buy_check.get("ema144_meso_slope", 0.0),
                                    },
                                },
                            })
                    elif prev_state == "S1":
                        # Stay in S1 - check buy conditions here (don't pass, handle it)
                        buy_check = self._check_buy_signal_conditions(contract, chain, features, ema_vals, price)
                        
                        if buy_check["entry_ready"]:
                            payload = self._build_payload("S1", features, {
                                "flag": {
                                    "s1_valid": True,
                                    "buy_signal": True,
                                    "entry_zone": buy_check["entry_zone"],
                                },
                                "scores": {
                                    "ts": buy_check["ts_score"],
                                    "ts_with_boost": buy_check.get("ts_with_boost", buy_check["ts_score"]),
                                },
                                "diagnostics": {
                                    "buy_check": {
                                        "entry_zone": buy_check.get("entry_zone", False),
                                        "slope_ok": buy_check.get("slope_ok", False),
                                        "ts_ok": buy_check.get("ts_ok", False),
                                        "ema60_slope": buy_check.get("ema60_meso_slope", 0.0),
                                        "ema144_slope": buy_check.get("ema144_meso_slope", 0.0),
                                    },
                                },
                            })
                        else:
                            payload = self._build_payload("S1", features, {
                                "flag": {"s1_valid": True},
                                "scores": {
                                    "ts": buy_check.get("ts_score", 0.0),
                                    "ts_with_boost": buy_check.get("ts_with_boost", buy_check.get("ts_score", 0.0)),
                                },
                                "diagnostics": {
                                    "buy_check": {
                                        "entry_zone": buy_check.get("entry_zone", False),
                                        "slope_ok": buy_check.get("slope_ok", False),
                                        "ts_ok": buy_check.get("ts_ok", False),
                                        "ema60_slope": buy_check.get("ema60_meso_slope", 0.0),
                                        "ema144_slope": buy_check.get("ema144_meso_slope", 0.0),
                                    },
                                },
                            })
                    # If not from S0 or S1, don't transition (stay in current state)
                
                # Enter S2: price > EMA333 from S1
                elif not payload and prev_state == "S1" and price > ema_vals["ema333"]:
                    payload = self._build_payload("S2", features, {
                        "flag": {"defensive": True},
                        "scores": {},
                    })
                
                # BUY SIGNAL: From S1 but price NOT > EMA60 (staying in S1, but outside entry zone initially)
                # This handles edge cases where we're in S1 but price dipped below EMA60 temporarily
                elif not payload and prev_state == "S1":
                    # Check buy signal conditions
                    buy_check = self._check_buy_signal_conditions(contract, chain, features, ema_vals, price)
                    
                    if buy_check["entry_ready"]:
                        # BUY signal triggered - emit from S1
                        meta = dict(features.get("uptrend_engine_v3_meta") or {})
                        s1_meta = dict(meta.get("s1") or {})
                        # Store EMA60 entry value for reference
                        if "ema60_entry" not in s1_meta:
                            s1_meta["ema60_entry"] = ema_vals["ema60"]
                            meta["s1"] = s1_meta
                            features["uptrend_engine_v3_meta"] = meta
                        
                        payload = self._build_payload("S1", features, {
                            "flag": {
                                "s1_valid": True,
                                "buy_signal": True,
                                "entry_zone": buy_check["entry_zone"],
                            },
                            "scores": {
                                "ts": buy_check["ts_score"],
                                "ts_with_boost": buy_check.get("ts_with_boost", buy_check["ts_score"]),
                            },
                            "levels": {
                                "base_sr_level": s1_meta.get("ema60_entry", ema_vals["ema60"]),
                            },
                            "diagnostics": {
                                "buy_check": {
                                    "entry_zone": buy_check.get("entry_zone", False),
                                    "slope_ok": buy_check.get("slope_ok", False),
                                    "ts_ok": buy_check.get("ts_ok", False),
                                    "ema60_slope": buy_check.get("ema60_meso_slope", 0.0),
                                    "ema144_slope": buy_check.get("ema144_meso_slope", 0.0),
                                },
                            },
                        })
                    else:
                        # Still in S1, no buy signal yet
                        payload = self._build_payload("S1", features, {
                            "flag": {"s1_valid": True},
                            "scores": {
                                "ts": buy_check.get("ts_score", 0.0),
                                "ts_with_boost": buy_check.get("ts_with_boost", buy_check.get("ts_score", 0.0)),
                            },
                            "diagnostics": {
                                "buy_check": {
                                    "entry_zone": buy_check.get("entry_zone", False),
                                    "slope_ok": buy_check.get("slope_ok", False),
                                    "ts_ok": buy_check.get("ts_ok", False),
                                    "ema60_slope": buy_check.get("ema60_meso_slope", 0.0),
                                    "ema144_slope": buy_check.get("ema144_meso_slope", 0.0),
                                },
                            },
                        })
                
                # S2 management (defensive regime)
                elif not payload and prev_state == "S2":
                    # Exit S2 -> S1 if price < EMA333
                    if price < ema_vals["ema333"]:
                        payload = self._build_payload("S1", features, {
                            "flag": {"s1_valid": True},
                            "scores": {},
                            "diagnostics": {"s2_to_s1": True, "reason": "price_below_ema333"},
                        })
                    else:
                        # Stay in S2
                        # Reuse S3 scoring to compute OX/DX for trim flags
                        s3_scores = self._compute_s3_scores(contract, chain, features)
                        ox = float(s3_scores["scores"].get("ox", 0.0))
                        trim_flag = ox >= Constants.OX_SELL_THRESHOLD
                        
                        # S2 retest-at-333 buy flag
                        ta_local = self._read_ta(features)
                        atr = ta_local.get("atr") or {}
                        atr_1h = float(atr.get("atr_1h") or 0.0)
                        entry_zone_333 = False
                        if ema_vals["ema333"] > 0 and atr_1h > 0:
                            entry_zone_333 = abs(price - ema_vals["ema333"]) <= (1.0 * atr_1h)
                        
                        slopes = (ta_local.get("ema_slopes") or {})
                        ema250_slope = float(slopes.get("ema250_slope") or 0.0)
                        ema333_slope = float(slopes.get("ema333_slope") or 0.0)
                        slope_ok_333 = (ema250_slope > 0.0) or (ema333_slope >= 0.0)
                        
                        # TS base and S/R boost anchored to EMA333
                        ts_block = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                        ts_base = float(ts_block.get("trend_strength") or 0.0)
                        ts_with_boost = ts_base
                        # Apply boost if S/R within halo of EMA333
                        sr_levels = self._read_sr_levels(features)
                        if sr_levels and ema_vals["ema333"] > 0 and atr_1h > 0:
                            halo = 1.0 * atr_1h
                            for sr in sr_levels[:10]:
                                try:
                                    sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                                    if sr_price > 0 and abs(sr_price - ema_vals["ema333"]) <= halo:
                                        sr_strength = float(sr.get("strength", 10) or 10)
                                        boost = min(0.15, (sr_strength / 20.0) * 0.15)
                                        ts_with_boost = min(1.0, ts_base + boost)
                                        break
                                except Exception:
                                    pass
                        
                        buy_flag = entry_zone_333 and slope_ok_333 and (ts_with_boost >= Constants.TS_ENTRY_THRESHOLD)
                        
                        payload = self._build_payload("S2", features, {
                            "flag": {
                                "defensive": True,
                                "trim_flag": trim_flag,
                                "buy_flag": buy_flag,
                                "entry_zone_333": entry_zone_333,
                            },
                            "scores": {
                                "ox": ox,
                                "ts": ts_base,
                                "ts_with_boost": ts_with_boost,
                            },
                        })
                
                # S2 → S3: full bullish alignment (band-based)
                elif not payload and prev_state == "S2" and self._check_bullish_alignment_band(ema_vals):
                    payload = self._build_payload("S3", features, {
                        "flags": {"trending": True},
                        "scores": {},
                        "diagnostics": {"s2_to_s3": True, "reason": "bullish_alignment_band"},
                    })

                # S3: All EMAs above 333 - ONLY from S2!
                elif not payload and prev_state == "S2" and self._check_bullish_alignment_band(ema_vals):
                    # Check for S3→S0 reset FIRST (all EMAs break below 333)
                    all_emas_below_333 = (
                        ema_vals["ema20"] < ema_vals["ema333"] and
                        ema_vals["ema30"] < ema_vals["ema333"] and
                        ema_vals["ema60"] < ema_vals["ema333"] and
                        ema_vals["ema144"] < ema_vals["ema333"] and
                        ema_vals["ema250"] < ema_vals["ema333"]
                    )
                    
                    if all_emas_below_333:
                        # Reset to S0
                        meta = dict(features.get("uptrend_engine_v3_meta") or {})
                        meta.pop("s1", None)
                        meta.pop("s2", None)
                        features["uptrend_engine_v3_meta"] = meta
                        payload = self._build_payload("S0", features, {
                            "flag": {"watch_only": True},
                            "scores": {},
                            "diagnostics": {"s3_reset": True, "reason": "all_emas_below_333"},
                        })
                    else:
                        # Stay in S3
                        s3_scores = self._compute_s3_scores(contract, chain, features)
                        ti_ts = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                        
                        # Check emergency exit
                        em_exit = self._check_emergency_exit(contract, chain, features, ema_vals, price, prev_payload)
                        
                        payload = self._build_payload("S3", features, {
                            "flags": {
                                "trending": True,
                                "dx_flag": s3_scores["flags"]["dx_flag"],
                                "emergency_exit": em_exit,
                            },
                            "scores": {
                                **s3_scores["scores"],
                                "ti": ti_ts["trend_integrity"],
                                "ts": ti_ts["trend_strength"],
                            },
                            "diagnostics": s3_scores["diagnostics"],
                        })
                        
                        # Add geometry context for S3 exits (kept for exits per spec)
                        try:
                            ta_local = self._read_ta(features)
                            atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                            last_px = price
                            halo = max(0.5 * atr_1h, 0.03 * last_px) if last_px > 0 else 0.0
                            
                            # Get S/R levels from geometry (for exit decisions)
                            sr_levels = self._read_sr_levels(features)
                            flipped_sr = []
                            for sr in sr_levels[:5]:  # Top 5 S/R levels
                                try:
                                    sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                                    if sr_price > 0:
                                        flipped_sr.append({
                                            "level": sr_price,
                                            "score": float(sr.get("strength", 10) or 10)
                                        })
                                except Exception:
                                    pass
                            
                            flipped_sr.sort(key=lambda x: float(x.get("level", 0.0)), reverse=True)
                            base_sr = float(flipped_sr[-1].get("level", 0.0)) if flipped_sr else 0.0
                            
                            payload["sr_context"] = {
                                "halo": halo,
                                "base_sr_level": base_sr,
                                "flipped_sr_levels": flipped_sr,
                            }
                        except Exception:
                            payload["sr_context"] = {}
                        
                        features = s3_scores["features"]
                        
                        # Check fakeout recovery (if emergency exit was active and price recovered)
                        prev_em_active = bool(prev_payload.get("flags", {}).get("emergency_exit", {}).get("active") or False)
                        if prev_em_active and price > ema_vals["ema333"]:
                            if ti_ts["trend_integrity"] >= Constants.TI_ENTRY_THRESHOLD and ti_ts["trend_strength"] >= Constants.TS_ENTRY_THRESHOLD:
                                # Fakeout recovery
                                payload["flags"]["fakeout_recovery"] = True
                                payload["flags"]["emergency_exit"] = {"active": False}
                                meta = dict(features.get("uptrend_engine_v3_meta") or {})
                                meta.pop("emergency_exit", None)
                                features["uptrend_engine_v3_meta"] = meta
                
                # Default fallback to S0
                if not payload:
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "scores": {},
                    })
                
                # Write payload
                new_features = dict(features)
                new_features["uptrend_engine_v3"] = payload
                self._write_features(pid, new_features)
                updated += 1
                
                # Log scores
                self._append_scores_log(contract, chain, payload["state"], payload.get("scores", {}))
                
                # Emit events on state transitions
                curr_state = payload["state"]
                if curr_state != prev_state:
                    event_payload = {"token_contract": contract, "chain": chain, "ts": now.isoformat(), "payload": payload}
                    if curr_state == "S1" and prev_state != "S1":
                        self._emit_event("s1_primer", event_payload)
                    if curr_state == "S2" and prev_state != "S2":
                        self._emit_event("s2_buy_signal", event_payload)
                    if curr_state == "S3" and prev_state != "S3":
                        self._emit_event("s3_trending", event_payload)
                
            except Exception as e:
                logger.debug("uptrend_engine_v3 skipped position: %s", e)
        
        logger.info("Uptrend engine v3 updated %d positions", updated)
        return updated

    def _check_emergency_exit(self, contract: str, chain: str, features: Dict[str, Any], ema_vals: Dict[str, float], price: float, prev_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Check emergency exit condition (price < EMA333)."""
        prev_em = prev_payload.get("flags", {}).get("emergency_exit", {})
        prev_active = bool(prev_em.get("active") or False)
        
        if price < ema_vals["ema333"]:
            # Activate emergency exit (single close, no persistence)
            last = self._latest_close_1h(contract, chain)
            ta = self._read_ta(features)
            atr = ta.get("atr", {})
            atr_1h = float(atr.get("atr_1h") or 0.0)
            halo = max(0.5 * atr_1h, 0.03 * price) if price > 0 else 0.0
            
            if not prev_active:
                # New activation - store break time in meta
                meta = dict(features.get("uptrend_engine_v3_meta") or {})
                em_meta = dict(meta.get("emergency_exit") or {})
                em_meta.update({
                    "break_time": _now_iso(),
                    "break_low": last.get("low") or price,
                    "ema333_at_break": ema_vals["ema333"],
                })
                meta["emergency_exit"] = em_meta
                features["uptrend_engine_v3_meta"] = meta
            
            # Read break info from meta
            meta = dict(features.get("uptrend_engine_v3_meta") or {})
            em_meta = dict(meta.get("emergency_exit") or {})
            break_time = str(em_meta.get("break_time") or _now_iso())
            break_low = float(em_meta.get("break_low") or price)
            ema333_at_break = float(em_meta.get("ema333_at_break") or ema_vals["ema333"])
            
            return {
                "active": True,
                "reason": "price_below_ema333",
                "ts": _now_iso(),
                "break_time": break_time,
                "break_low": break_low,
                "ema333_at_break": ema333_at_break,
                "halo": halo,
                "bounce_zone": {
                    "low": ema_vals["ema333"] - halo,
                    "high": ema_vals["ema333"] + halo,
                },
            }
        else:
            # Price recovered - emergency exit inactive
            return {"active": False}


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    UptrendEngineV3().run()


if __name__ == "__main__":
    main()


