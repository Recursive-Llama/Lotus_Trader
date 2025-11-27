"""
Uptrend Engine v4 - Clean EMA Phase System

Based on UPTREND_ENGINE_V4_SPEC.md

Key improvements:
- Uses ta_utils.py for all TA calculations (single source of truth)
- Simplified S0→S1 transition (no acceleration patterns, no persistence)
- Buy signal directly from S1 (no separate S2 entry state)
- S2 as defensive regime (price > EMA333, not full alignment)
- Diagnostics always populated (not optional)
- Bootstrap logic: only S0 or S3, otherwise no state

Architecture: Engine emits signals/flags; Portfolio Manager/Backtester makes decisions.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import statistics
import math

from supabase import create_client, Client  # type: ignore

from src.intelligence.lowcap_portfolio_manager.jobs.ta_utils import (
    ema_series,
    lin_slope,
    ema_slope_normalized,
    avwap_series,
    atr_series_wilder,
    adx_series_wilder,
    rsi,
)
from src.intelligence.lowcap_portfolio_manager.utils.zigzag import detect_swings

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Constants:
    """v4 Constants - from spec and reused from v2 for OX/DX/EDX
    
    All thresholds are easily tunable here for quick adjustments.
    """
    
    # TS gate for buy signals (S1, S2 retest, S3 DX buys)
    # Fixed at 0.60: requires TS base >= 0.35 with 0.25 S/R boost to pass
    # This filters weak trends while still allowing entries when S/R aligns
    TS_THRESHOLD = 0.60  # Fixed threshold (was 0.58, tried 0.50 but too lenient)
    
    # S/R boost maximum (applied when S/R level within halo of anchor EMA)
    SR_BOOST_MAX = 0.25  # Increased from 0.15 (more aggressive when S/R aligns)
    
    # Entry zone (halo)
    ENTRY_HALO_ATR_MULTIPLIER = 1.0
    
    # S2 retest halo (EMA333 retest buys) - easily tunable
    S2_RETEST_HALO_ATR_MULTIPLIER = 0.5  # 0.5 * ATR (was 0.3, too tight)
    
    # OX trim threshold (S2 and S3)
    OX_SELL_THRESHOLD = 0.65
    
    # DX buy threshold (S3) - base threshold before EDX suppression and price position adjustments
    DX_BUY_THRESHOLD = 0.60  # Lowered from 0.65 (was too strict, many near misses)
    
    # Emergency exit TI/TS thresholds for fakeout recovery
    EMERGENCY_EXIT_TI_MIN = 0.50
    EMERGENCY_EXIT_TS_MIN = 0.50
    
    # OX/DX/EDX constants (from v2)
    ADX_FLOOR = 18.0
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


class UptrendEngineV4:
    """Uptrend Engine v4 - EMA Phase System.
    
    Responsibilities:
    - Detect state using EMA hierarchy (band-based)
    - Compute TS scores for entry quality gates
    - Compute OX/DX/EDX scores for S3 regime management
    - Emit signals and flags (does NOT make trading decisions)
    - Write live snapshot to features.uptrend_engine_v4
    
    Architecture: Engine emits signals; Portfolio Manager/Backtester makes decisions.
    """

    def __init__(self, timeframe: str = "1h") -> None:
        """
        Initialize Uptrend Engine v4.
        
        Args:
            timeframe: Timeframe to process ("1m", "15m", "1h", "4h")
        """
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.timeframe = timeframe
        # Map timeframe to TA suffix (e.g., "1m" -> "_1m", "1h" -> "_1h")
        self.ta_suffix = f"_{timeframe}"

    # --------------- Data access helpers ---------------
    
    def _active_positions(self) -> List[Dict[str, Any]]:
        """Get positions for this timeframe (watchlist, active - skip dormant/paused/archived).
        
        Note: Dormant positions (< 350 bars) are skipped - not enough data for analysis.
        Watchlist positions (≥ 350 bars) are processed for bootstrap/warmup (no signals).
        Active positions are processed normally (signals enabled).
        """
        res = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,features,status")
            .eq("timeframe", self.timeframe)
            .in_("status", ["watchlist", "active"])  # Skip dormant - not enough data
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _write_features(self, pid: Any, features: Dict[str, Any]) -> None:
        update_payload: Dict[str, Any] = {"features": features}
        uptrend_payload = (features or {}).get("uptrend_engine_v4") or {}
        state_value = uptrend_payload.get("state")
        if state_value:
            update_payload["state"] = state_value
        self.sb.table("lowcap_positions").update(update_payload).eq("id", pid).execute()

    def _emit_event(self, event: str, payload: Dict[str, Any]) -> None:
        """Emit state change event to database."""
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
        """Append scores to historical log."""
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
        """Read TA data from features."""
        return features.get("ta") or {}
    
    def _read_sr_levels(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Read S/R levels from geometry (used for exits and optional entry boost)."""
        geom = features.get("geometry") or {}
        levels = ((geom.get("levels") or {}).get("sr_levels") or [])
        return list(levels)

    def _get_ema_values(self, ta: Dict[str, Any]) -> Dict[str, float]:
        """Extract EMA values from TA block (timeframe-specific)."""
        ema = ta.get("ema") or {}
        suffix = self.ta_suffix
        return {
            "ema20": float(ema.get(f"ema20{suffix}") or 0.0),
            "ema30": float(ema.get(f"ema30{suffix}") or 0.0),
            "ema60": float(ema.get(f"ema60{suffix}") or 0.0),
            "ema144": float(ema.get(f"ema144{suffix}") or 0.0),
            "ema250": float(ema.get(f"ema250{suffix}") or 0.0),
            "ema333": float(ema.get(f"ema333{suffix}") or 0.0),
        }
    
    def _get_ema_slopes(self, ta: Dict[str, Any]) -> Dict[str, float]:
        """Extract EMA slopes from TA block (already normalized %/bar from ta_tracker)."""
        slopes = ta.get("ema_slopes") or {}
        suffix = self.ta_suffix
        return {
            "ema20_slope": float(slopes.get(f"ema20_slope{suffix}") or 0.0),
            "ema60_slope": float(slopes.get(f"ema60_slope{suffix}") or 0.0),
            "ema144_slope": float(slopes.get(f"ema144_slope{suffix}") or 0.0),
            "ema250_slope": float(slopes.get(f"ema250_slope{suffix}") or 0.0),
            "ema333_slope": float(slopes.get(f"ema333_slope{suffix}") or 0.0),
        }

    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
        """Get latest close price (bar close for deterministic checks) - timeframe-specific."""
        row = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_usd, low_usd")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", self.timeframe)
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
                "close": float(r.get("close_usd") or 0.0),
                "low": float(r.get("low_usd") or 0.0),
            }
        return {"ts": None, "close": 0.0, "low": 0.0}

    def _get_atr(self, ta: Dict[str, Any]) -> float:
        """Get ATR from TA (timeframe-specific)."""
        atr_data = ta.get("atr") or {}
        suffix = self.ta_suffix
        return float(atr_data.get(f"atr{suffix}") or 0.0)

    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 400) -> List[Dict[str, Any]]:
        """Fetch recent OHLC bars (timeframe-specific)."""
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", self.timeframe)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        rows.reverse()
        return rows

    def _fetch_ohlc_since(self, contract: str, chain: str, since_iso: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch OHLC bars since a timestamp (for S3 window calculations) - timeframe-specific."""
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", self.timeframe)
            .gte("timestamp", since_iso)
            .order("timestamp", desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows

    def _get_s3_start_ts(self, features: Dict[str, Any]) -> Optional[str]:
        """Get S3 start timestamp from metadata."""
        meta = features.get("uptrend_engine_v4_meta") or {}
        return str(meta.get("s3_start_ts")) if meta.get("s3_start_ts") else None

    def _set_s3_start_ts(self, pid: Any, features: Dict[str, Any], ts: str) -> None:
        """Set S3 start timestamp in metadata."""
        if "uptrend_engine_v4_meta" not in features:
            features["uptrend_engine_v4_meta"] = {}
        features["uptrend_engine_v4_meta"]["s3_start_ts"] = ts
        self._write_features(pid, features)

    def _clear_s3_start_ts(self, pid: Any, features: Dict[str, Any]) -> None:
        """Clear S3 start timestamp from metadata."""
        if "uptrend_engine_v4_meta" in features and "s3_start_ts" in features["uptrend_engine_v4_meta"]:
            del features["uptrend_engine_v4_meta"]["s3_start_ts"]
            self._write_features(pid, features)

    def _calculate_window_boundaries(self, s3_start_ts: str, current_ts: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Calculate window boundaries for 3-window EDX approach.
        
        Returns:
            (window1_bars, window2_bars, window3_bars) - number of bars for each window
            None if window is too small (< 10 bars minimum)
        """
        try:
            start_dt = datetime.fromisoformat(s3_start_ts.replace("Z", "+00:00"))
            current_dt = datetime.fromisoformat(current_ts.replace("Z", "+00:00"))
            total_bars = int((current_dt - start_dt).total_seconds() / 3600)  # 1 hour per bar
            
            if total_bars < 10:
                # Not enough bars for meaningful windows
                return (None, None, None)
            
            # Window 1: Full duration (since S3 start)
            window1_bars = total_bars
            
            # Window 2: Last 2/3
            window2_bars = int(total_bars * 2 / 3)
            if window2_bars < 10:
                window2_bars = None
            
            # Window 3: Last 1/3 (must be > 9 bars per requirement)
            window3_bars = int(total_bars / 3)
            if window3_bars <= 9:
                window3_bars = None
            
            return (window1_bars, window2_bars, window3_bars)
        except Exception:
            return (None, None, None)

    def _calculate_bars_since_s3_entry(self, s3_start_ts: Optional[str], current_ts: str) -> Optional[int]:
        """Calculate number of bars since S3 entry.
        
        Returns:
            Number of bars (1 hour per bar) or None if S3 start timestamp not available
        """
        if not s3_start_ts:
            return None
        try:
            start_dt = datetime.fromisoformat(s3_start_ts.replace("Z", "+00:00"))
            current_dt = datetime.fromisoformat(current_ts.replace("Z", "+00:00"))
            bars = int((current_dt - start_dt).total_seconds() / 3600)  # 1 hour per bar
            return max(0, bars)
        except Exception:
            return None

    def _check_first_dip_buy(
        self,
        contract: str,
        chain: str,
        price: float,
        ema_vals: Dict[str, float],
        ta: Dict[str, Any],
        features: Dict[str, Any],
        current_ts: str,
    ) -> Dict[str, Any]:
        """Check first dip buy conditions.
        
        Two options:
        1. Price within 0.5*ATR of EMA20/30, within first 6 bars of S3
        2. Price within 0.5*ATR of EMA60, within first 12 bars of S3
        
        Both require:
        - TS + S/R boost >= 0.50 (lower threshold than normal 0.60)
        - Slope OK: EMA144_slope > 0.0 OR EMA250_slope >= 0.0
        - First dip buy not already taken (one-time flag)
        - Price >= EMA333 (emergency exit blocks first dip buys)
        
        Note: If price dips below EMA333 and then reclaims, first dip buy can still trigger
        if still within the time window (bars 0-6 for EMA20/30, or bars 0-12 for EMA60).
        
        Returns:
            Dict with first_dip_buy_flag and diagnostics
        """
        # Check if first dip buy already taken
        meta = features.get("uptrend_engine_v4_meta") or {}
        if meta.get("first_dip_buy_taken", False):
            return {
                "first_dip_buy_flag": False,
                "diagnostics": {"reason": "already_taken"},
            }
        
        # Get S3 start timestamp
        s3_start_ts = self._get_s3_start_ts(features)
        if not s3_start_ts:
            return {
                "first_dip_buy_flag": False,
                "diagnostics": {"reason": "no_s3_start_ts"},
            }
        
        # Calculate bars since S3 entry
        bars_since_entry = self._calculate_bars_since_s3_entry(s3_start_ts, current_ts)
        if bars_since_entry is None:
            return {
                "first_dip_buy_flag": False,
                "diagnostics": {"reason": "cannot_calculate_bars"},
            }
        
        # Get EMAs
        ema20 = ema_vals.get("ema20", 0.0)
        ema30 = ema_vals.get("ema30", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        
        if ema20 <= 0 or ema30 <= 0 or ema60 <= 0 or ema333 <= 0:
            return {
                "first_dip_buy_flag": False,
                "diagnostics": {"reason": "invalid_emas"},
            }
        
        # Emergency exit check: Block first dip buy if price < EMA333
        # Rationale: Below EMA333 is emergency exit territory - too risky for first dip buys
        # Once EMA333 is reclaimed (price >= EMA333), first dip buys can resume if still within time window
        emergency_exit = price < ema333
        if emergency_exit:
            return {
                "first_dip_buy_flag": False,
                "diagnostics": {"reason": "emergency_exit_below_333"},
            }
        
        # Get ATR
        atr_val = self._get_atr(ta)
        if atr_val <= 0:
            return {
                "first_dip_buy_flag": False,
                "diagnostics": {"reason": "invalid_atr"},
            }
        
        # Check slope: EMA144/250 (not 250/333)
        ema_slopes = ta.get("ema_slopes") or {}
        ema144_slope = float(ema_slopes.get("ema144_slope", 0.0))
        ema250_slope = float(ema_slopes.get("ema250_slope", 0.0))
        slope_ok = (ema144_slope > 0.0) or (ema250_slope >= 0.0)
        
        # Check TS + S/R boost >= 0.50 (lower threshold for first dip)
        ts_score = self._compute_ts(ta)
        sr_levels = self._read_sr_levels(features)
        # S/R boost anchored to EMA333 for consistency
        sr_boost = self._compute_sr_boost(price, ema333, atr_val, sr_levels)
        ts_with_boost = ts_score + sr_boost
        ts_ok = ts_with_boost >= 0.50  # Lower threshold for first dip
        
        # Check option 1: EMA20/30 within first 6 bars
        halo_20_30 = 0.5 * atr_val
        dist_20 = abs(price - ema20)
        dist_30 = abs(price - ema30)
        near_20_30 = (dist_20 <= halo_20_30) or (dist_30 <= halo_20_30)
        option1_ok = (bars_since_entry <= 6) and near_20_30
        
        # Check option 2: EMA60 within first 12 bars
        halo_60 = 0.5 * atr_val
        dist_60 = abs(price - ema60)
        near_60 = dist_60 <= halo_60
        option2_ok = (bars_since_entry <= 12) and near_60
        
        # First dip buy if either option is met AND slope + TS OK
        first_dip_buy_flag = (option1_ok or option2_ok) and slope_ok and ts_ok
        
        diagnostics = {
            "bars_since_entry": bars_since_entry,
            "option1_ema20_30": option1_ok,
            "option2_ema60": option2_ok,
            "dist_ema20": dist_20,
            "dist_ema30": dist_30,
            "dist_ema60": dist_60,
            "halo_20_30": halo_20_30,
            "halo_60": halo_60,
            "slope_ok": slope_ok,
            "ema144_slope": ema144_slope,
            "ema250_slope": ema250_slope,
            "ts_ok": ts_ok,
            "ts_score": ts_score,
            "ts_with_boost": ts_with_boost,
            "sr_boost": sr_boost,
            "emergency_exit": False,  # Already checked above, but include for diagnostics
            "first_dip_buy_flag": first_dip_buy_flag,
        }
        
        return {
            "first_dip_buy_flag": first_dip_buy_flag,
            "diagnostics": diagnostics,
        }

    # --------------- EMA Order Checks (Band-based) ---------------

    def _check_s0_order(self, ema_vals: Dict[str, float]) -> bool:
        """Check perfect bearish order (band-based).
        
        S0: EMA20 < EMA60 AND EMA30 < EMA60 (fast band below mid)
        AND EMA60 < EMA144 < EMA250 < EMA333 (slow descending)
        """
        ema20 = ema_vals.get("ema20", 0.0)
        ema30 = ema_vals.get("ema30", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        
        # Fast band below mid
        fast_below_mid = (ema20 < ema60) and (ema30 < ema60)
        
        # Slow descending
        slow_descending = (ema60 < ema144) and (ema144 < ema250) and (ema250 < ema333)
        
        return fast_below_mid and slow_descending

    def _check_s3_order(self, ema_vals: Dict[str, float]) -> bool:
        """Check full bullish alignment (band-based).
        
        S3: EMA20 > EMA60 AND EMA30 > EMA60 (fast band above mid)
        AND EMA60 > EMA144 > EMA250 > EMA333 (slow ascending)
        """
        ema20 = ema_vals.get("ema20", 0.0)
        ema30 = ema_vals.get("ema30", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        
        # Fast band above mid
        fast_above_mid = (ema20 > ema60) and (ema30 > ema60)
        
        # Slow ascending
        slow_ascending = (ema60 > ema144) and (ema144 > ema250) and (ema250 > ema333)
        
        return fast_above_mid and slow_ascending

    def _check_fast_band_above_60(self, ema_vals: Dict[str, float]) -> bool:
        """Check if fast band (20/30) is above EMA60."""
        ema20 = ema_vals.get("ema20", 0.0)
        ema30 = ema_vals.get("ema30", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        return (ema20 > ema60) and (ema30 > ema60)

    def _check_fast_band_at_bottom(self, ema_vals: Dict[str, float]) -> bool:
        """Check if fast band (20/30) is at the bottom (below all other EMAs).
        
        Global exit precedence: exits position immediately.
        """
        ema20 = ema_vals.get("ema20", 0.0)
        ema30 = ema_vals.get("ema30", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        
        bottom_ema = min(ema60, ema144, ema250, ema333)
        return (ema20 < bottom_ema) and (ema30 < bottom_ema)

    # --------------- TS Calculation (from v2/v3) ---------------

    def _compute_ts(self, ta: Dict[str, Any]) -> float:
        """Compute Trend Strength (TS) score.
        
        TS = (RSI_slope_weight + ADX_slope_weight) / 2
        
        Reused from v2/v3.
        """
        momentum = ta.get("momentum") or {}
        rsi_slope = float(momentum.get("rsi_slope_10") or 0.0)
        adx_slope = float(momentum.get("adx_slope_10") or 0.0)
        
        # Normalize RSI slope (typically -100 to +100, target 0-1)
        rsi_weight = max(0.0, min(1.0, (rsi_slope + 5.0) / 10.0))
        
        # Normalize ADX slope (typically -20 to +20, target 0-1)
        adx_weight = max(0.0, min(1.0, (adx_slope + 2.0) / 4.0))
        
        ts = (rsi_weight + adx_weight) / 2.0
        return max(0.0, min(1.0, ts))

    def _compute_sr_boost(self, price: float, ema_anchor: float, atr: float, sr_levels: List[Dict[str, Any]]) -> float:
        """Compute S/R boost up to +0.15 if S/R level within halo of anchor EMA.
        
        Args:
            price: Current price
            ema_anchor: EMA60 (S1) or EMA333 (S2 retest)
            atr: ATR value
            sr_levels: List of S/R level dicts with 'price' and 'strength' keys
        """
        if not sr_levels or atr <= 0.0:
            return 0.0
        
        halo = Constants.ENTRY_HALO_ATR_MULTIPLIER * atr
        
        max_boost = 0.0
        for level in sr_levels:
            level_price = float(level.get("price") or 0.0)
            level_strength = float(level.get("strength") or 0.0)
            
            distance = abs(level_price - ema_anchor)
            if distance <= halo:
                # Boost proportional to strength and proximity
                proximity_factor = 1.0 - (distance / halo)
                boost = level_strength * proximity_factor * Constants.SR_BOOST_MAX
                max_boost = max(max_boost, boost)
        
        return min(max_boost, Constants.SR_BOOST_MAX)

    # --------------- Buy Signal Conditions ---------------

    def _check_buy_signal_conditions(
        self,
        price: float,
        ema_anchor: float,
        ema_slopes: Dict[str, float],
        ta: Dict[str, Any],
        sr_levels: List[Dict[str, Any]],
        anchor_is_333: bool = False,
    ) -> Dict[str, Any]:
        """Check buy signal conditions (S1 buy or S2 retest buy).
        
        Args:
            price: Current price
            ema_anchor: EMA60 (S1) or EMA333 (S2 retest)
            ema_slopes: EMA slopes dict
            ta: Full TA dict
            sr_levels: S/R levels list
            anchor_is_333: If True, use EMA250/EMA333 slopes; else EMA60/EMA144
        
        Returns:
            Dict with condition checks and diagnostics
        """
        atr = self._get_atr(ta)
        # Use different halo per regime: S1 (EMA60) uses 1.0 * ATR, S2 retest (EMA333) uses tunable multiplier
        halo = (Constants.S2_RETEST_HALO_ATR_MULTIPLIER * atr) if anchor_is_333 else (Constants.ENTRY_HALO_ATR_MULTIPLIER * atr)
        
        # 1. Entry zone: abs(price - ema_anchor) <= halo
        # For S2 retest buys: price must be within halo of EMA333 (can be above or at EMA333)
        # Since we're already in S2 (price >= EMA333), just check the halo distance
        if anchor_is_333:
            # S2 retest: price within halo of EMA333 (typically price >= EMA333 since we're in S2)
            entry_zone_ok = abs(price - ema_anchor) <= halo
        else:
            # S1 buy: price can be above or below EMA60, just within halo
            entry_zone_ok = abs(price - ema_anchor) <= halo
        
        # 2. Slope OK: 
        if anchor_is_333:
            # S2 retest: EMA250_slope > 0.0 OR EMA333_slope >= 0.0
            slope_ok = (ema_slopes.get("ema250_slope", 0.0) > 0.0) or (ema_slopes.get("ema333_slope", 0.0) >= 0.0)
        else:
            # S1 buy: EMA60_slope > 0.0 OR EMA144_slope >= 0.0
            slope_ok = (ema_slopes.get("ema60_slope", 0.0) > 0.0) or (ema_slopes.get("ema144_slope", 0.0) >= 0.0)
        
        # 3. TS gate: TS + S/R boost >= 0.58
        ts_score = self._compute_ts(ta)
        sr_boost = self._compute_sr_boost(price, ema_anchor, atr, sr_levels)
        ts_with_boost = ts_score + sr_boost
        ts_ok = ts_with_boost >= Constants.TS_THRESHOLD
        
        # Diagnostics (always populated)
        diagnostics = {
            "entry_zone_ok": entry_zone_ok,
            "slope_ok": slope_ok,
            "ts_ok": ts_ok,
            "ts_score": ts_score,
            "ts_with_boost": ts_with_boost,
            "sr_boost": sr_boost,
            "atr": atr,
            "halo": halo,
            "price": price,
            "ema_anchor": ema_anchor,
        }
        
        if anchor_is_333:
            diagnostics["ema250_slope"] = ema_slopes.get("ema250_slope", 0.0)
            diagnostics["ema333_slope"] = ema_slopes.get("ema333_slope", 0.0)
        else:
            diagnostics["ema60_slope"] = ema_slopes.get("ema60_slope", 0.0)
            diagnostics["ema144_slope"] = ema_slopes.get("ema144_slope", 0.0)
        
        buy_signal = entry_zone_ok and slope_ok and ts_ok
        
        return {
            "buy_signal": buy_signal,
            "diagnostics": diagnostics,
        }

    # --------------- OX/DX/EDX Calculations ---------------

    def _compute_edx_3window(
        self,
        contract: str,
        chain: str,
        s3_start_ts: str,
        current_ts: str,
        price: float,
        ema_vals: Dict[str, float],
        ta: Dict[str, Any],
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute EDX using 3-window S3-relative approach.
        
        Components:
        1. Slow-Field Momentum (30%): EMA250/333 slopes, RSI trend, ADX trend (3 windows)
        2. Structure Failure (25%): ZigZag HH/HL ratio (3 windows)
        3. Participation Decay (20%): AVWAP slope (3 windows)
        4. EMA Structure Compression (10%): EMA144-333, EMA250-333 separations (3 windows)
        
        Returns:
            (edx_score, diagnostics_dict)
        """
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        # Calculate window boundaries
        w1_bars, w2_bars, w3_bars = self._calculate_window_boundaries(s3_start_ts, current_ts)
        
        if w1_bars is None:
            # Not enough bars, return neutral EDX
            return (0.5, {"error": "insufficient_s3_bars", "s3_bars": 0})
        
        # Fetch all bars since S3 start
        all_bars = self._fetch_ohlc_since(contract, chain, s3_start_ts, limit=500)
        if len(all_bars) < 10:
            return (0.5, {"error": "insufficient_data", "bars": len(all_bars)})
        
        # Extract data
        closes = [float(b.get("close_usd") or 0.0) for b in all_bars]
        highs = [float(b.get("high_usd") or 0.0) for b in all_bars]
        lows = [float(b.get("low_usd") or 0.0) for b in all_bars]
        volumes = [float(b.get("volume") or 0.0) for b in all_bars]
        
        # Calculate ATR series for ZigZag
        bars_for_atr = [
            {"h": h, "l": l, "c": c}
            for h, l, c in zip(highs, lows, closes)
        ]
        atr_series = atr_series_wilder(bars_for_atr, period=14)
        if len(atr_series) != len(closes):
            # Pad if needed
            atr_series = [atr_series[0]] * (len(closes) - len(atr_series)) + atr_series
        
        # Helper to get window data
        def get_window_data(bars_count: Optional[int]) -> Tuple[List[float], List[float], List[float], List[float], List[float]]:
            """Get closes, highs, lows, volumes, atrs for a window."""
            if bars_count is None:
                return ([], [], [], [], [])
            window_bars = all_bars[-bars_count:] if bars_count > 0 else []
            return (
                [float(b.get("close_usd") or 0.0) for b in window_bars],
                [float(b.get("high_usd") or 0.0) for b in window_bars],
                [float(b.get("low_usd") or 0.0) for b in window_bars],
                [float(b.get("volume") or 0.0) for b in window_bars],
                atr_series[-bars_count:] if bars_count <= len(atr_series) else atr_series,
            )
        
        # 1. SLOW-FIELD MOMENTUM (30%): EMA250/333 slopes, RSI trend, ADX trend
        def compute_slow_field_momentum(window_closes: List[float], window_bars: List[Dict[str, Any]]) -> float:
            """Compute slow-field momentum score for a window."""
            if len(window_closes) < 10:
                return 0.5  # Neutral
            
            # EMA250/333 slopes
            ema250_series = ema_series(window_closes, 250)
            ema333_series = ema_series(window_closes, 333)
            
            # Use last 20 bars for slope calculation if available
            slope_window = min(20, len(ema250_series))
            ema250_slope = ema_slope_normalized(ema250_series[-slope_window:], window=min(10, slope_window))
            ema333_slope = ema_slope_normalized(ema333_series[-slope_window:], window=min(10, slope_window))
            
            # Average of normalized slopes (positive = good, negative = decay)
            ema_slope_score = (ema250_slope + ema333_slope) / 2.0
            ema_score = sigmoid(ema_slope_score * 1000.0, 1.0)  # Normalize to 0-1
            
            # RSI trend (slope of RSI series)
            rsi_vals: List[float] = []
            for i in range(14, len(window_closes)):
                rsi_vals.append(rsi(window_closes[:i+1], 14))
            if len(rsi_vals) >= 10:
                rsi_slope = lin_slope(rsi_vals, 10)
                rsi_score = sigmoid(rsi_slope / 5.0, 1.0)  # Normalize
            else:
                rsi_score = 0.5
            
            # ADX trend (slope of ADX series)
            bars_dicts = [{"h": h, "l": l, "c": c} for h, l, c in 
                         zip([float(b.get("high_usd") or 0.0) for b in window_bars],
                             [float(b.get("low_usd") or 0.0) for b in window_bars],
                             window_closes)]
            adx_series_vals = adx_series_wilder(bars_dicts, period=14)
            if len(adx_series_vals) >= 10:
                adx_slope = lin_slope(adx_series_vals, 10)
                adx_score = sigmoid(adx_slope / 2.0, 1.0)  # Normalize
            else:
                adx_score = 0.5
            
            # Combined score (average)
            return (ema_score + rsi_score + adx_score) / 3.0
        
        # 2. STRUCTURE FAILURE (25%): ZigZag HH/HL ratio
        def compute_structure_failure(window_closes: List[float], window_highs: List[float], 
                                     window_lows: List[float], window_atrs: List[float]) -> float:
            """Compute structure failure score using ZigZag HH/HL ratio."""
            if len(window_closes) < 10:
                return 0.5  # Neutral
            
            try:
                swings = detect_swings(window_closes, window_atrs, highs=window_highs, lows=window_lows,
                                      lambda_mult=1.2, backstep=3, min_leg_bars=4)
                pivots = swings.get("pivots", [])
                
                if len(pivots) < 4:
                    return 0.5  # Not enough pivots
                
                # Count HH vs LH and HL vs LL
                hh_count = 0
                lh_count = 0
                hl_count = 0
                ll_count = 0
                
                highs_only = [(i, p) for i, p in pivots if p == 'H']
                lows_only = [(i, p) for i, p in pivots if p == 'L']
                
                # Higher Highs / Lower Highs
                for k in range(1, len(highs_only)):
                    prev_idx, _ = highs_only[k-1]
                    curr_idx, _ = highs_only[k]
                    if curr_idx < len(window_closes) and prev_idx < len(window_closes):
                        if window_closes[curr_idx] > window_closes[prev_idx]:
                            hh_count += 1
                        else:
                            lh_count += 1
                
                # Higher Lows / Lower Lows
                for k in range(1, len(lows_only)):
                    prev_idx, _ = lows_only[k-1]
                    curr_idx, _ = lows_only[k]
                    if curr_idx < len(window_closes) and prev_idx < len(window_closes):
                        if window_closes[curr_idx] > window_closes[prev_idx]:
                            hl_count += 1
                        else:
                            ll_count += 1
                
                total_swings = hh_count + lh_count + hl_count + ll_count
                if total_swings == 0:
                    return 0.5
                
                # HH/HL ratio (higher = better structure)
                hh_hl_ratio = (hh_count + hl_count) / total_swings
                
                # Invert for decay score (lower ratio = higher decay)
                return 1.0 - hh_hl_ratio
            except Exception:
                return 0.5
        
        # 3. PARTICIPATION DECAY (20%): AVWAP slope
        def compute_participation_decay(window_closes: List[float], window_volumes: List[float]) -> float:
            """Compute participation decay score using AVWAP slope."""
            if len(window_closes) < 10 or not window_closes or not window_volumes:
                return 0.5  # Neutral
            
            # Calculate AVWAP series
            avwap_vals = avwap_series(window_closes, window_volumes)
            if len(avwap_vals) < 10:
                return 0.5
            
            # Calculate AVWAP slope (last 10 bars)
            slope_window = min(10, len(avwap_vals))
            avwap_slope = lin_slope(avwap_vals[-slope_window:], slope_window)
            
            # Normalize by latest AVWAP value
            latest_avwap = avwap_vals[-1] if avwap_vals else 1.0
            avwap_slope_pct = avwap_slope / max(latest_avwap, 1e-9)
            
            # Positive slope = good participation, negative = decay
            return sigmoid(-avwap_slope_pct * 1000.0, 1.0)  # Invert (decay = high score)
        
        # 4. EMA STRUCTURE COMPRESSION (10%): EMA144-333, EMA250-333 separations
        def compute_structure_compression(window_closes: List[float]) -> float:
            """Compute EMA structure compression score."""
            if len(window_closes) < 144:
                return 0.5  # Need at least 144 bars for EMA144
            
            # Calculate EMAs
            ema144_series = ema_series(window_closes, 144)
            ema250_series = ema_series(window_closes, 250)
            ema333_series = ema_series(window_closes, 333)
            
            if len(ema144_series) < 10 or len(ema250_series) < 10 or len(ema333_series) < 10:
                return 0.5
            
            # Calculate separations over last 10 bars
            sep_window = min(10, len(ema144_series))
            sep144_333 = [(ema144_series[i] - ema333_series[i]) / max(ema333_series[i], 1e-9) 
                         for i in range(len(ema144_series)-sep_window, len(ema144_series))]
            sep250_333 = [(ema250_series[i] - ema333_series[i]) / max(ema333_series[i], 1e-9)
                         for i in range(len(ema250_series)-sep_window, len(ema250_series))]
            
            # Calculate separation trends (slopes)
            sep144_333_slope = lin_slope(sep144_333, len(sep144_333))
            sep250_333_slope = lin_slope(sep250_333, len(sep250_333))
            
            # Negative slope = compression = decay
            avg_compression = (sep144_333_slope + sep250_333_slope) / 2.0
            return sigmoid(-avg_compression * 100.0, 1.0)  # Invert (compression = high score)
        
        # Compute scores for each window
        w1_closes, w1_highs, w1_lows, w1_vols, w1_atrs = get_window_data(w1_bars)
        w1_bars_list = all_bars[-w1_bars:] if w1_bars else []
        
        slow1 = compute_slow_field_momentum(w1_closes, w1_bars_list) if w1_closes else 0.5
        struct1 = compute_structure_failure(w1_closes, w1_highs, w1_lows, w1_atrs) if w1_closes else 0.5
        part1 = compute_participation_decay(w1_closes, w1_vols) if w1_closes else 0.5
        comp1 = compute_structure_compression(w1_closes) if w1_closes else 0.5
        
        slow2, struct2, part2, comp2 = 0.5, 0.5, 0.5, 0.5
        if w2_bars:
            w2_closes, w2_highs, w2_lows, w2_vols, w2_atrs = get_window_data(w2_bars)
            w2_bars_list = all_bars[-w2_bars:] if w2_bars else []
            slow2 = compute_slow_field_momentum(w2_closes, w2_bars_list) if w2_closes else 0.5
            struct2 = compute_structure_failure(w2_closes, w2_highs, w2_lows, w2_atrs) if w2_closes else 0.5
            part2 = compute_participation_decay(w2_closes, w2_vols) if w2_closes else 0.5
            comp2 = compute_structure_compression(w2_closes) if w2_closes else 0.5
        
        slow3, struct3, part3, comp3 = 0.5, 0.5, 0.5, 0.5
        if w3_bars:
            w3_closes, w3_highs, w3_lows, w3_vols, w3_atrs = get_window_data(w3_bars)
            w3_bars_list = all_bars[-w3_bars:] if w3_bars else []
            slow3 = compute_slow_field_momentum(w3_closes, w3_bars_list) if w3_closes else 0.5
            struct3 = compute_structure_failure(w3_closes, w3_highs, w3_lows, w3_atrs) if w3_closes else 0.5
            part3 = compute_participation_decay(w3_closes, w3_vols) if w3_closes else 0.5
            comp3 = compute_structure_compression(w3_closes) if w3_closes else 0.5
        
        # Compare windows: decay = w3 > w2 > w1 (declining trend health)
        # If w3 score > w2 > w1, trend is weakening
        def decay_score(score1: float, score2: Optional[float], score3: Optional[float]) -> float:
            """Calculate decay score from 3-window comparison."""
            if score2 is None:
                # Only window 1 available
                return score1
            if score3 is None:
                # Only windows 1 and 2 available
                if score2 > score1:
                    return (score1 * 0.3) + (score2 * 0.7)  # Recent weakening
                else:
                    return (score1 + score2) / 2.0  # Stable or improving
            
            # All 3 windows available
            # Decay pattern: w3 > w2 > w1 (all increasing = decay accelerating)
            if score3 > score2 > score1:
                return (score1 * 0.2) + (score2 * 0.3) + (score3 * 0.5)  # Weight recent more
            elif score2 > score1:
                # Recent weakening
                return (score1 * 0.3) + (score2 * 0.7)
            else:
                # Stable or improving
                return (score1 + score2) / 2.0
        
        slow_decay = decay_score(slow1, slow2 if w2_bars else None, slow3 if w3_bars else None)
        struct_decay = decay_score(struct1, struct2 if w2_bars else None, struct3 if w3_bars else None)
        part_decay = decay_score(part1, part2 if w2_bars else None, part3 if w3_bars else None)
        comp_decay = decay_score(comp1, comp2 if w2_bars else None, comp3 if w3_bars else None)
        
        # Weighted composite (volatility disorder removed)
        edx_score = (
            0.30 * slow_decay +
            0.25 * struct_decay +
            0.20 * part_decay +
            0.10 * comp_decay
        )
        edx_score = max(0.0, min(1.0, edx_score))
        
        diagnostics = {
            "edx_slow": slow_decay,
            "edx_struct": struct_decay,
            "edx_part": part_decay,
            "edx_geom": comp_decay,
            "window1_bars": w1_bars,
            "window2_bars": w2_bars,
            "window3_bars": w3_bars,
            "w1_slow": slow1,
            "w1_struct": struct1,
            "w1_part": part1,
            "w1_comp": comp1,
            "w2_slow": slow2 if w2_bars else None,
            "w2_struct": struct2 if w2_bars else None,
            "w2_part": part2 if w2_bars else None,
            "w2_comp": comp2 if w2_bars else None,
            "w3_slow": slow3 if w3_bars else None,
            "w3_struct": struct3 if w3_bars else None,
            "w3_part": part3 if w3_bars else None,
            "w3_comp": comp3 if w3_bars else None,
        }
        
        return (edx_score, diagnostics)
    
    def _compute_edx_fallback(self, ta: Dict[str, Any], ema_vals: Dict[str, float], 
                              contract: str, chain: str) -> Tuple[float, Dict[str, Any]]:
        """Fallback EDX calculation (old method) if S3 start timestamp not available."""
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        slopes = ta.get("ema_slopes") or {}
        ema250_slope = float(slopes.get("ema250_slope") or 0.0)
        ema333_slope = float(slopes.get("ema333_slope") or 0.0)
        slow_down = sigmoid(-(ema250_slope) / Constants.S3_EDX_SLOW_K, 1.0) * 0.5 + sigmoid(-(ema333_slope) / Constants.S3_EDX_SLOW_333_K, 1.0) * 0.5
        
        rows = self._fetch_recent_ohlc(contract, chain, limit=50)
        closes = [float(r.get("close_usd") or 0.0) for r in rows]
        lows = [float(r.get("low_usd") or 0.0) for r in rows]
        ema60 = ema_vals.get("ema60", 0.0)
        below_mid_ratio = 0.0
        if ema60 > 0.0 and closes:
            below_mid_ratio = sum(1 for c in closes if c < ema60) / float(len(closes) or 1)
        ll_ratio = 0.0
        if len(lows) >= 2:
            ll_ratio = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i - 1]) / float(len(lows) - 1)
        struct = 0.5 * sigmoid((ll_ratio - 0.5) / 0.2, 1.0) + 0.5 * sigmoid((below_mid_ratio - 0.4) / 0.2, 1.0)
        
        vol = ta.get("volume") or {}
        suffix = self.ta_suffix
        vo_z = float(vol.get(f"vo_z{suffix}") or 0.0)
        part_decay = sigmoid(-(vo_z) / 1.0, 1.0)
        
        sep = ta.get("separations") or {}
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        geom_roll = 0.6 * sigmoid(-(dsep_mid) / Constants.S3_EXP_MID_K, 1.0) + 0.4 * sigmoid(-(dsep_fast) / Constants.S3_EXP_FAST_K, 1.0)
        
        edx_score = 0.30 * slow_down + 0.25 * struct + 0.20 * part_decay + 0.10 * geom_roll
        edx_score = max(0.0, min(1.0, edx_score))
        
        return (edx_score, {
            "edx_slow": slow_down,
            "edx_struct": struct,
            "edx_part": part_decay,
            "edx_geom": geom_roll,
            "fallback": True,
        })

    def _compute_ox_only(
        self,
        price: float,
        ema_vals: Dict[str, float],
        ta: Dict[str, Any],
    ) -> float:
        """Compute OX (Overextension) score only - no EDX, no database calls.
        
        Used in S2 for trim flags. Does not require S3 context or database access.
        """
        ema = ta.get("ema") or {}
        sep = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        mom = ta.get("momentum") or {}
        
        px = price
        atr_val = self._get_atr(ta)
        suffix = self.ta_suffix
        atr_mean_20 = float(atr.get("atr_mean_20") or (atr_val if atr_val else 1.0))
        ema20 = ema_vals.get("ema20", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        slopes = ta.get("ema_slopes") or {}
        ema20_slope = float(slopes.get("ema20_slope") or 0.0)
        
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        # OX: rails distance + expansion + ATR surge + fragility (same as S3)
        rail_fast = sigmoid(((px - ema20) / max(atr_val * Constants.S3_RAIL_FAST_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        rail_mid = sigmoid(((px - ema60) / max(atr_val * Constants.S3_RAIL_MID_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        rail_144 = sigmoid(((px - ema144) / max(atr_val * Constants.S3_RAIL_144_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        rail_250 = sigmoid(((px - ema250) / max(atr_val * Constants.S3_RAIL_250_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        exp_fast = sigmoid(dsep_fast / Constants.S3_EXP_FAST_K, 1.0)
        exp_mid = sigmoid(dsep_mid / Constants.S3_EXP_MID_K, 1.0)
        atr_surge = sigmoid((atr_val / max(atr_mean_20, 1e-9)) - 1.0, 1.0)
        fragility = sigmoid(-ema20_slope / Constants.S1_CURVATURE_K, 1.0)
        ox_base = (
            0.35 * rail_fast + 0.20 * rail_mid + 0.10 * rail_144 + 0.10 * rail_250 +
            0.10 * exp_fast + 0.05 * exp_mid + 0.05 * atr_surge + 0.05 * fragility
        )
        # No EDX boost in S2 (EDX only makes sense in S3 context)
        ox = max(0.0, min(1.0, ox_base))
        return ox
    
    def _compute_s3_scores(
        self,
        contract: str,
        chain: str,
        price: float,
        ema_vals: Dict[str, float],
        ta: Dict[str, Any],
        features: Dict[str, Any],
        current_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compute OX/DX/EDX scores for S3 regime.
        
        EDX now uses 3-window S3-relative approach:
        - Window 1: Since S3 start (full duration)
        - Window 2: Last 2/3 of S3
        - Window 3: Last 1/3 of S3
        
        Returns scores and diagnostics.
        """
        ema = ta.get("ema") or {}
        sep = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        mom = ta.get("momentum") or {}
        vol = ta.get("volume") or {}
        suffix = self.ta_suffix
        vo_z = float(vol.get(f"vo_z{suffix}") or 0.0)
        
        px = price
        atr_val = self._get_atr(ta)
        atr_mean_20 = float(atr.get("atr_mean_20") or (atr_val if atr_val else 1.0))
        ema20 = ema_vals.get("ema20", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        slopes = ta.get("ema_slopes") or {}
        ema20_slope = float(slopes.get("ema20_slope") or 0.0)
        d_ema144_slope = float(slopes.get("d_ema144_slope") or 0.0)
        
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        # Get current timestamp (prefer passed parameter, fallback to database, then now)
        if current_ts:
            pass  # Use provided timestamp (from backtester context)
        else:
            last_bar = self._latest_close_1h(contract, chain)
            current_ts = last_bar.get("ts") or _now_iso()
        
        # Get S3 start timestamp
        s3_start_ts = self._get_s3_start_ts(features)
        
        # Compute EDX using 3-window approach if we have S3 start timestamp
        if s3_start_ts:
            edx, edx_diagnostics = self._compute_edx_3window(
                contract, chain, s3_start_ts, current_ts, price, ema_vals, ta
            )
        else:
            # Fallback: use old method if no S3 start timestamp (shouldn't happen in S3, but safety)
            edx, edx_diagnostics = self._compute_edx_fallback(ta, ema_vals, contract, chain)
        
        edx_raw = edx  # For now, EDX is raw (can add smoothing later if needed)
        
        # Merge EDX diagnostics into main diagnostics
        diagnostics_dict = {**edx_diagnostics}
        
        # OX: rails distance + expansion + ATR surge + fragility (unchanged from v2)
        rail_fast = sigmoid(((px - ema20) / max(atr_val * Constants.S3_RAIL_FAST_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        rail_mid = sigmoid(((px - ema60) / max(atr_val * Constants.S3_RAIL_MID_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        rail_144 = sigmoid(((px - ema144) / max(atr_val * Constants.S3_RAIL_144_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        rail_250 = sigmoid(((px - ema250) / max(atr_val * Constants.S3_RAIL_250_K, 1e-9)), 1.0) if atr_val > 0 else 0.0
        exp_fast = sigmoid(dsep_fast / Constants.S3_EXP_FAST_K, 1.0)
        exp_mid = sigmoid(dsep_mid / Constants.S3_EXP_MID_K, 1.0)
        atr_surge = sigmoid((atr_val / max(atr_mean_20, 1e-9)) - 1.0, 1.0)
        fragility = sigmoid(-ema20_slope / Constants.S1_CURVATURE_K, 1.0)
        ox_base = (
            0.35 * rail_fast + 0.20 * rail_mid + 0.10 * rail_144 + 0.10 * rail_250 +
            0.10 * exp_fast + 0.05 * exp_mid + 0.05 * atr_surge + 0.05 * fragility
        )
        edx_boost = max(0.0, min(0.5, edx - 0.5))
        ox = max(0.0, min(1.0, ox_base * (1.0 + 0.33 * edx_boost)))
        
        # DX: hallway 144→333, exhaustion/relief/curl
        # In S3, order is EMA144 > EMA250 > EMA333 (descending)
        # We want high score when price is near EMA333 (deep discount), low when near EMA144
        if ema144 > ema333 and (ema144 - ema333) > 0 and px > 0:
            # S3 order: EMA144 (top) → EMA333 (bottom of hallway, deepest discount)
            # x = 0 when price = EMA333 (deepest, highest score)
            # x = 1 when price = EMA144 (shallowest, lowest score)
            x = max(0.0, min(1.0, (px - ema333) / max((ema144 - ema333), 1e-9)))
            band_width = ema144 - ema333
        elif ema333 > ema144 and (ema333 - ema144) > 0 and px > 0:
            # Ascending order (shouldn't happen in S3, but handle for safety)
            # EMA144 (bottom) → EMA333 (top)
            # x = 0 when price = EMA144, x = 1 when price = EMA333
            x = max(0.0, min(1.0, (px - ema144) / max((ema333 - ema144), 1e-9)))
            band_width = ema333 - ema144
        else:
            # Fallback: can't calculate, set x to give low score
            x = 1.0 if px <= ema144 else 0.0
            band_width = abs(ema333 - ema144) if (ema333 != ema144) else max(ema333, ema144) * 0.01
        
        # Compression multiplier: higher score when EMA144-333 band is compressed (tight)
        comp_mult = sigmoid((0.03 - (band_width / max(px, 1e-9))) / 0.02, 1.0)
        # exp(-3.0 * x): high when x is small (near EMA333), low when x is large (near EMA144)
        dx_location = math.exp(-3.0 * x) * (1.0 + 0.3 * comp_mult)
        exhaustion = max(0.0, min(1.0, sigmoid(-vo_z / 1.0, 1.0)))
        atr_relief = sigmoid(((atr_val / max(atr_mean_20, 1e-9)) - 0.9) / 0.05, 1.0)
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
        
        # Update diagnostics with EDX components (removed old edx_vol_dis)
        diagnostics_dict.update({
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
        })
        
        return {
            "ox": ox,
            "dx": dx,
            "edx": edx,
            "diagnostics": diagnostics_dict,
        }

    # --------------- State Machine Logic ---------------

    def _build_payload(
        self,
        state: str,
        contract: str,
        chain: str,
        price: float,
        ema_vals: Dict[str, float],
        features: Dict[str, Any],
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build state payload with diagnostics."""
        payload = {
            "token_contract": contract,
            "chain": chain,
            "ts": _now_iso(),
            "state": state,
            "price": price,
            "ema": ema_vals,
            **extra,  # Includes diagnostics, flags, scores, etc.
            "meta": {"updated_at": _now_iso()},
        }
        return payload

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
                position_status = p.get("status", "active")  # Get position status
                features = p.get("features") or {}
                prev_payload = dict(features.get("uptrend_engine_v4") or {})
                prev_state = str(prev_payload.get("state") or "")
                
                ta = self._read_ta(features)
                if not ta:
                    continue
                
                ema_vals = self._get_ema_values(ta)
                ema_slopes = self._get_ema_slopes(ta)
                last = self._latest_close_1h(contract, chain)
                price = last["close"]
                
                if price <= 0:
                    continue
                
                sr_levels = self._read_sr_levels(features)
                
                # Track watchlist status for diagnostics (signals are now emitted regardless of status)
                # Dormant positions are skipped entirely (not enough data)
                is_watchlist = (position_status == "watchlist")
                
                # Bootstrap logic: only S0 or S3, otherwise no state
                if not prev_state or prev_state == "":
                    if self._check_s3_order(ema_vals):
                        # Bootstrap to S3: Record S3 start timestamp
                        current_ts = last.get("ts") or _now_iso()
                        self._set_s3_start_ts(pid, features, current_ts)
                        
                        # Compute S3 scores for bootstrap
                        s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta, features)
                        
                        # For dormant positions: write diagnostics but still allow signals
                        extra_data = {
                            "trending": True,
                            "scores": {
                                "ox": s3_scores.get("ox", 0.0),
                                "dx": s3_scores.get("dx", 0.0),
                                "edx": s3_scores.get("edx", 0.0),
                            },
                            "diagnostics": s3_scores.get("diagnostics", {}),
                        }
                        
                        payload = self._build_payload(
                            "S3",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            extra_data,
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                        continue
                    elif self._check_s0_order(ema_vals):
                        prev_state = "S0"
                    else:
                        # No state - wait until clear trend emerges
                        payload = self._build_payload(
                            "S4",  # or "no_state"
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {"watch_only": True},
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                        continue
                
                # Global exit precedence: fast band at bottom (overrides all states)
                if self._check_fast_band_at_bottom(ema_vals):
                    payload = self._build_payload(
                        "S0",
                        contract,
                        chain,
                        price,
                        ema_vals,
                        features,
                        {
                            "exit_position": True,
                            "exit_reason": "fast_band_at_bottom",
                        },
                    )
                    features["uptrend_engine_v4"] = payload
                    self._write_features(pid, features)
                    self._emit_event("uptrend_state_change", payload)
                    updated += 1
                    continue
                
                # --------------- State Machine Logic ---------------
                
                # S0: Pure Downtrend
                if prev_state == "S0":
                    # S0 → S1: Fast band above EMA60 AND Price > EMA60 (must come from S0)
                    if self._check_fast_band_above_60(ema_vals) and price > ema_vals.get("ema60", 0.0):
                        # Check buy signal conditions
                        buy_check = self._check_buy_signal_conditions(
                            price, ema_vals.get("ema60", 0.0), ema_slopes, ta, sr_levels, anchor_is_333=False
                        )
                        
                        extra_data = {
                            "buy_signal": buy_check.get("buy_signal", False),
                            "diagnostics": {"buy_check": buy_check.get("diagnostics", {})},
                        }
                        payload = self._build_payload(
                            "S1",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            extra_data,
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    else:
                        # Stay in S0
                        payload = self._build_payload(
                            "S0",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {},
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                
                # S1: Primer (looking for entries at EMA60)
                elif prev_state == "S1":
                    # Check buy signal conditions (always check, always populate diagnostics)
                    buy_check = self._check_buy_signal_conditions(
                        price, ema_vals.get("ema60", 0.0), ema_slopes, ta, sr_levels, anchor_is_333=False
                    )
                    
                    # S1 → S2: Price > EMA333 (flip-flop, not an exit)
                    if price > ema_vals.get("ema333", 0.0):
                        payload = self._build_payload(
                            "S2",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "diagnostics": {},  # S2 diagnostics added below
                            },
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    else:
                        # Stay in S1 (always populate buy_check diagnostics)
                        extra_data = {
                            "buy_signal": buy_check.get("buy_signal", False),
                            "diagnostics": {"buy_check": buy_check.get("diagnostics", {})},
                        }
                        payload = self._build_payload(
                            "S1",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            extra_data,
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                
                # S2: Defensive Regime (price > EMA333, not full alignment)
                elif prev_state == "S2":
                    # S2 → S1: Price < EMA333 (flip-flop back, not an exit)
                    if price < ema_vals.get("ema333", 0.0):
                        payload = self._build_payload(
                            "S1",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "diagnostics": {},  # Will be populated when staying in S1
                            },
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    # S2 → S3: Full bullish alignment (band-based)
                    elif self._check_s3_order(ema_vals):
                        # Record S3 start timestamp
                        current_ts = last.get("ts") or _now_iso()
                        self._set_s3_start_ts(pid, features, current_ts)
                        
                        payload = self._build_payload(
                            "S3",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "diagnostics": {},  # S3 scores added below
                            },
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    else:
                        # Stay in S2: Check trims and retest buys
                        # S2 only needs OX, not EDX (EDX requires S3 context)
                        ox = self._compute_ox_only(price, ema_vals, ta)
                        
                        # Trim flag: OX >= 0.65 AND price within 1×ATR of S/R level
                        atr_val = self._get_atr(ta)
                        sr_halo = 1.0 * atr_val
                        near_sr = False
                        if sr_levels and atr_val > 0:
                            for level in sr_levels:
                                level_price = float(level.get("price") or 0.0)
                                if level_price > 0 and abs(price - level_price) <= sr_halo:
                                    near_sr = True
                                    break
                        trim_flag = (ox >= Constants.OX_SELL_THRESHOLD) and near_sr
                        
                        # Retest buy at EMA333
                        retest_check = self._check_buy_signal_conditions(
                            price, ema_vals.get("ema333", 0.0), ema_slopes, ta, sr_levels, anchor_is_333=True
                        )
                        
                        extra_data = {
                            "trim_flag": trim_flag,
                            "buy_flag": retest_check.get("buy_signal", False),
                            "scores": {"ox": ox},
                            "diagnostics": {
                                "s2_retest_check": retest_check.get("diagnostics", {}),
                            },
                        }
                        payload = self._build_payload(
                            "S2",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            extra_data,
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                
                # S4: Holding pattern waiting for trend clarity
                elif prev_state == "S4":
                    if self._check_s3_order(ema_vals):
                        current_ts = last.get("ts") or _now_iso()
                        self._set_s3_start_ts(pid, features, current_ts)
                        s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta, features)
                        extra_data = {
                            "trending": True,
                            "scores": {
                                "ox": s3_scores.get("ox", 0.0),
                                "dx": s3_scores.get("dx", 0.0),
                                "edx": s3_scores.get("edx", 0.0),
                            },
                            "diagnostics": s3_scores.get("diagnostics", {}),
                        }
                        payload = self._build_payload(
                            "S3",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            extra_data,
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    elif self._check_s0_order(ema_vals):
                        payload = self._build_payload(
                            "S0",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {"diagnostics": {"bootstrap": "S0_from_S4"}},
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    else:
                        payload = self._build_payload(
                            "S4",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {"watch_only": True},
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                
                # S3: Trending (full bullish alignment)
                elif prev_state == "S3":
                    # S3 → S0: All EMAs break below EMA333
                    all_below_333 = (
                        ema_vals.get("ema20", 0.0) < ema_vals.get("ema333", 0.0) and
                        ema_vals.get("ema30", 0.0) < ema_vals.get("ema333", 0.0) and
                        ema_vals.get("ema60", 0.0) < ema_vals.get("ema333", 0.0) and
                        ema_vals.get("ema144", 0.0) < ema_vals.get("ema333", 0.0) and
                        ema_vals.get("ema250", 0.0) < ema_vals.get("ema333", 0.0)
                    )
                    
                    if all_below_333:
                        # Clear S3 start timestamp and first dip buy flag on exit
                        self._clear_s3_start_ts(pid, features)
                        if "uptrend_engine_v4_meta" in features and "first_dip_buy_taken" in features["uptrend_engine_v4_meta"]:
                            del features["uptrend_engine_v4_meta"]["first_dip_buy_taken"]
                            self._write_features(pid, features)
                        
                        payload = self._build_payload(
                            "S0",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {"exit_position": True, "exit_reason": "all_emas_below_333"},
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        self._emit_event("uptrend_state_change", payload)
                        updated += 1
                    else:
                        # Stay in S3: Compute scores, check emergency exit
                        s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta, features)
                        
                        ema333_val = ema_vals.get("ema333", 0.0)
                        
                        # Get current timestamp for first dip buy check
                        current_ts = last.get("ts") or _now_iso()
                        
                        # Check first dip buy (only if not already taken)
                        first_dip_check = self._check_first_dip_buy(
                            contract, chain, price, ema_vals, ta, features, current_ts
                        )
                        first_dip_buy_flag = first_dip_check.get("first_dip_buy_flag", False)
                        
                        # Set flag if first dip buy triggered
                        if first_dip_buy_flag:
                            if "uptrend_engine_v4_meta" not in features:
                                features["uptrend_engine_v4_meta"] = {}
                            features["uptrend_engine_v4_meta"]["first_dip_buy_taken"] = True
                        
                        # Emergency exit: price < EMA333 (flag only, no state change)
                        emergency_exit = price < ema333_val
                        
                        # Reclaimed EMA333: price transitions from < EMA333 to >= EMA333 (in S3)
                        # Check if previous bar had emergency_exit flag
                        prev_emergency_exit = bool(prev_payload.get("emergency_exit", False))
                        reclaimed_ema333 = False
                        if prev_emergency_exit and price >= ema333_val:
                            # Price was below EMA333 (emergency exit active), now reclaimed
                            reclaimed_ema333 = True
                        
                        ox = s3_scores.get("ox", 0.0)
                        dx = s3_scores.get("dx", 0.0)
                        edx = s3_scores.get("edx", 0.0)
                        
                        # S3 DX buy requires: DX >= threshold AND price <= EMA144 AND slope OK AND TS gate
                        # EDX sliding scale: buying power decreases as EDX rises (suppresses DX threshold)
                        # Price position sliding scale: buying power highest near EMA333, decreases as price moves to EMA144
                        ema144_val = ema_vals.get("ema144", 0.0)
                        ema333_val = ema_vals.get("ema333", 0.0)
                        
                        # Price must be <= EMA144 to be in discount zone
                        price_in_discount_zone = price <= ema144_val if ema144_val > 0 else False
                        
                        # 1. Slope OK: EMA250_slope > 0.0 OR EMA333_slope >= 0.0 (same as S2 retest)
                        # Slow band health check - ensures trend structure is intact
                        ema_slopes = ta.get("ema_slopes") or {}
                        ema250_slope = float(ema_slopes.get("ema250_slope", 0.0))
                        ema333_slope = float(ema_slopes.get("ema333_slope", 0.0))
                        slope_ok = (ema250_slope > 0.0) or (ema333_slope >= 0.0)
                        
                        # 2. TS Gate: TS + S/R boost >= 0.58 (same as S1/S2 entries)
                        # Trend Strength check - ensures momentum is supportive
                        ts_score = self._compute_ts(ta)
                        sr_levels = self._read_sr_levels(features)
                        atr_val = self._get_atr(ta)
                        # S/R boost anchored to EMA333 for S3 (same as S2 retest)
                        sr_boost = self._compute_sr_boost(price, ema333_val, atr_val, sr_levels)
                        ts_with_boost = ts_score + sr_boost
                        ts_ok = ts_with_boost >= Constants.TS_THRESHOLD
                        
                        # EDX suppression: as EDX rises, require higher DX to trigger buy (less aggressive)
                        # Per SM_UPTREND.MD: "As EDX rises, all discount/rebuy (DX) opportunities are progressively diminished"
                        # EDX 0.0-0.5: no suppression (fresh trend, all rebuys at full strength)
                        # EDX 0.5-0.7: moderate suppression (smooth transition)
                        # EDX 0.7+: high suppression (requires much higher DX, essentially shutting down adds)
                        edx_suppression = 0.0
                        if edx >= 0.7:
                            edx_suppression = 0.15  # Require DX >= 0.80 (high decay regime)
                        elif edx >= 0.5:
                            edx_suppression = (edx - 0.5) * 0.5  # Linear from 0.0 to 0.10
                        dx_threshold_adjusted = Constants.DX_BUY_THRESHOLD + edx_suppression
                        
                        # Price position boost: buying power highest near EMA333 (retest zone), decreases toward EMA144
                        # Rationale: Near EMA333 is a "retest" - more reliable support, less risk
                        # Near EMA144 is "deep discount" - more risk, require better DX to justify
                        price_position_boost = 0.0
                        if price_in_discount_zone and ema333_val > ema144_val and (ema333_val - ema144_val) > 0:
                            # Normalize price position in band: 0.0 at EMA144, 1.0 at EMA333
                            band_width = ema333_val - ema144_val
                            price_pos = (price - ema144_val) / band_width
                            # Near EMA333 (pos=1.0): boost (more aggressive, lower threshold)
                            # Near EMA144 (pos=0.0): penalty (less aggressive, higher threshold)
                            # Boost range: -0.05 to +0.10 (allows buys closer to EMA333 with same DX)
                            price_position_boost = (price_pos * 0.10) - ((1.0 - price_pos) * 0.05)
                        dx_threshold_final = max(0.0, dx_threshold_adjusted - price_position_boost)
                        
                        # Final check: ALL conditions must be met
                        # Emergency exit: Block DX buys when price < EMA333 (too risky)
                        # Once EMA333 is reclaimed, DX buys can resume if all other conditions are met
                        dx_ok = dx >= dx_threshold_final
                        dx_buy_ok = dx_ok and price_in_discount_zone and slope_ok and ts_ok and not emergency_exit
                        
                        # Note: ts_score, sr_boost, ts_with_boost already computed above for buy check
                        
                        # Trim flag: OX >= 0.65 AND price within 1×ATR of S/R level
                        atr_val = self._get_atr(ta)
                        sr_halo = 1.0 * atr_val
                        near_sr = False
                        if sr_levels and atr_val > 0:
                            for level in sr_levels:
                                level_price = float(level.get("price") or 0.0)
                                if level_price > 0 and abs(price - level_price) <= sr_halo:
                                    near_sr = True
                                    break
                        trim_flag = (ox >= Constants.OX_SELL_THRESHOLD) and near_sr
                        
                        extra_data = {
                            "trim_flag": trim_flag,
                            "buy_flag": dx_buy_ok,
                            "first_dip_buy_flag": first_dip_buy_flag,
                            "emergency_exit": emergency_exit,
                            "reclaimed_ema333": reclaimed_ema333,
                            "scores": {
                                "ox": ox,
                                "dx": dx,
                                "edx": edx,
                                "ts": ts_score,
                                "ts_with_boost": ts_with_boost,
                                "sr_boost": sr_boost,
                            },
                            "diagnostics": {
                                **s3_scores.get("diagnostics", {}),
                                "s3_buy_check": {
                                    "price": price,
                                    "ema144": ema144_val,
                                    "ema333": ema333_val,
                                    "price_in_discount_zone": price_in_discount_zone,
                                    "dx": dx,
                                    "dx_threshold_base": Constants.DX_BUY_THRESHOLD,
                                    "edx_suppression": edx_suppression,
                                        "dx_threshold_adjusted": dx_threshold_adjusted,
                                        "price_position_boost": price_position_boost,
                                        "dx_threshold_final": dx_threshold_final,
                                        "dx_ok": dx_ok,
                                        "slope_ok": slope_ok,
                                        "ema250_slope": ema250_slope,
                                        "ema333_slope": ema333_slope,
                                        "ts_ok": ts_ok,
                                        "ts_score": ts_score,
                                        "ts_with_boost": ts_with_boost,
                                        "sr_boost": sr_boost,
                                        "emergency_exit": emergency_exit,
                                        "buy_flag": dx_buy_ok,
                                    },
                                    "first_dip_buy_check": first_dip_check.get("diagnostics", {}),
                                },
                            },
                        payload = self._build_payload(
                            "S3",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            extra_data,
                        )
                        features["uptrend_engine_v4"] = payload
                        self._write_features(pid, features)
                        updated += 1
                
                # Unknown state - treat as no state
                else:
                    # Wait for bootstrap to determine state
                    continue
                
            except Exception as e:
                logger.debug("uptrend_engine_v4 error on position %s: %s", p.get("id"), e)
                continue
        
        return updated


def main(timeframe: str = "1h") -> None:
    """Entry point for running engine.
    
    Args:
        timeframe: Timeframe to process ("1m", "15m", "1h", "4h")
    """
    import logging
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    engine = UptrendEngineV4(timeframe=timeframe)
    updated = engine.run()
    logger.info("Uptrend Engine v4 (%s) updated %d positions", timeframe, updated)


if __name__ == "__main__":
    main()

