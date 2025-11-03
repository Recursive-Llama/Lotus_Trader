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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import statistics

from supabase import create_client, Client  # type: ignore

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Constants:
    """v4 Constants - from spec and reused from v2 for OX/DX/EDX"""
    
    # TS gate for buy signals
    TS_THRESHOLD = 0.58
    
    # S/R boost maximum
    SR_BOOST_MAX = 0.15
    
    # Entry zone (halo)
    ENTRY_HALO_ATR_MULTIPLIER = 1.0
    
    # S2 retest halo (EMA333 retest buys) - easily tunable
    S2_RETEST_HALO_ATR_MULTIPLIER = 0.5  # 0.5 * ATR (was 0.3, too tight)
    
    # OX trim threshold (S2 and S3)
    OX_SELL_THRESHOLD = 0.65
    
    # DX buy threshold (S3)
    DX_BUY_THRESHOLD = 0.65
    
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
    
    def _get_ema_slopes(self, ta: Dict[str, Any]) -> Dict[str, float]:
        """Extract EMA slopes from TA block (already normalized %/bar from ta_tracker)."""
        slopes = ta.get("ema_slopes") or {}
        return {
            "ema20_slope": float(slopes.get("ema20_slope") or 0.0),
            "ema60_slope": float(slopes.get("ema60_slope") or 0.0),
            "ema144_slope": float(slopes.get("ema144_slope") or 0.0),
            "ema250_slope": float(slopes.get("ema250_slope") or 0.0),
            "ema333_slope": float(slopes.get("ema333_slope") or 0.0),
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

    def _get_atr(self, ta: Dict[str, Any]) -> float:
        """Get ATR from TA."""
        atr_data = ta.get("atr") or {}
        return float(atr_data.get("atr_1h") or 0.0)

    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 400) -> List[Dict[str, Any]]:
        """Fetch recent OHLC bars."""
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

    # --------------- OX/DX/EDX Calculations (from v2) ---------------

    def _compute_s3_scores(
        self,
        contract: str,
        chain: str,
        price: float,
        ema_vals: Dict[str, float],
        ta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute OX/DX/EDX scores for S3 regime (from v2, reused as-is).
        
        Returns scores and diagnostics.
        """
        import math
        
        ema = ta.get("ema") or {}
        sep = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        mom = ta.get("momentum") or {}
        vol = ta.get("volume") or {}
        slopes = ta.get("ema_slopes") or {}
        
        px = price
        atr_1h = float(atr.get("atr_1h") or 0.0)
        atr_mean_20 = float(atr.get("atr_mean_20") or (atr_1h if atr_1h else 1.0))
        ema20 = ema_vals.get("ema20", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        vo_z_1h = float(vol.get("vo_z_1h") or 0.0)
        ema20_slope = float(slopes.get("ema20_slope") or 0.0)
        d_ema144_slope = float(slopes.get("d_ema144_slope") or 0.0)
        
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        # EDX (expanded composite)
        ema250_slope = float(slopes.get("ema250_slope") or 0.0)
        ema333_slope = float(slopes.get("ema333_slope") or 0.0)
        slow_down = sigmoid(-(ema250_slope) / Constants.S3_EDX_SLOW_K, 1.0) * 0.5 + sigmoid(-(ema333_slope) / Constants.S3_EDX_SLOW_333_K, 1.0) * 0.5
        
        # Structure failure approximations
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
        part_decay = sigmoid(-(vo_z_1h) / 1.0, 1.0)
        
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
        up_avg = statistics.fmean(ups) if ups else (sum(trs) / len(trs) if trs else 0.0)
        down_avg = statistics.fmean(downs) if downs else (sum(trs) / len(trs) if trs else 0.0)
        asym = 0.0
        if up_avg > 0.0:
            asym = sigmoid(((down_avg / up_avg) - 1.0) / 0.2, 1.0)
        
        # Geometry rollover
        geom_roll = 0.6 * sigmoid(-(dsep_mid) / Constants.S3_EXP_MID_K, 1.0) + 0.4 * sigmoid(-(dsep_fast) / Constants.S3_EXP_FAST_K, 1.0)
        
        # Weighted composite
        edx_raw = 0.30 * slow_down + 0.25 * struct + 0.20 * part_decay + 0.15 * asym + 0.10 * geom_roll
        edx_raw = max(0.0, min(1.0, edx_raw))
        
        # Smooth EDX with EMA
        # Note: v4 doesn't have meta tracking yet, so we'll use raw for now
        # Can be enhanced later if needed
        edx = edx_raw
        
        # OX: rails distance + expansion + ATR surge + fragility
        rail_fast = sigmoid(((px - ema20) / max(atr_1h * Constants.S3_RAIL_FAST_K, 1e-9)), 1.0) if atr_1h > 0 else 0.0
        rail_mid = sigmoid(((px - ema60) / max(atr_1h * Constants.S3_RAIL_MID_K, 1e-9)), 1.0) if atr_1h > 0 else 0.0
        rail_144 = sigmoid(((px - ema144) / max(atr_1h * Constants.S3_RAIL_144_K, 1e-9)), 1.0) if atr_1h > 0 else 0.0
        rail_250 = sigmoid(((px - ema250) / max(atr_1h * Constants.S3_RAIL_250_K, 1e-9)), 1.0) if atr_1h > 0 else 0.0
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
            "ox": ox,
            "dx": dx,
            "edx": edx,
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
                
                # Bootstrap logic: only S0 or S3, otherwise no state
                if not prev_state or prev_state == "":
                    if self._check_s3_order(ema_vals):
                        prev_state = "S3"
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
                        
                        payload = self._build_payload(
                            "S1",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "buy_signal": buy_check.get("buy_signal", False),
                                "diagnostics": {"buy_check": buy_check.get("diagnostics", {})},
                            },
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
                        payload = self._build_payload(
                            "S1",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "buy_signal": buy_check.get("buy_signal", False),
                                "diagnostics": {"buy_check": buy_check.get("diagnostics", {})},
                            },
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
                        s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta)
                        ox = s3_scores.get("ox", 0.0)
                        
                        # Trim flag on pumps
                        trim_flag = ox >= Constants.OX_SELL_THRESHOLD
                        
                        # Retest buy at EMA333
                        retest_check = self._check_buy_signal_conditions(
                            price, ema_vals.get("ema333", 0.0), ema_slopes, ta, sr_levels, anchor_is_333=True
                        )
                        
                        payload = self._build_payload(
                            "S2",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "trim_flag": trim_flag,
                                "buy_flag": retest_check.get("buy_signal", False),
                                "scores": {"ox": ox},
                                "diagnostics": {
                                    "s2_retest_check": retest_check.get("diagnostics", {}),
                                },
                            },
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
                        s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta)
                        
                        # Emergency exit: price < EMA333 (flag only, no state change)
                        emergency_exit = price < ema_vals.get("ema333", 0.0)
                        
                        # Fakeout recovery: price reclaims EMA333 + TI/TS thresholds
                        fakeout_recovery = False
                        if emergency_exit:
                            # Check if price reclaimed (would need to track previous emergency exit)
                            # For now, just flag emergency exit
                            pass
                        
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
                        dx_ok = dx >= dx_threshold_final
                        dx_buy_ok = dx_ok and price_in_discount_zone and slope_ok and ts_ok
                        
                        # Note: ts_score, sr_boost, ts_with_boost already computed above for buy check
                        
                        payload = self._build_payload(
                            "S3",
                            contract,
                            chain,
                            price,
                            ema_vals,
                            features,
                            {
                                "trim_flag": ox >= Constants.OX_SELL_THRESHOLD,
                                "buy_flag": dx_buy_ok,
                                "emergency_exit": emergency_exit,
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
                                        "buy_flag": dx_buy_ok,
                                    },
                                },
                            },
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


def main() -> None:
    """Entry point for running engine."""
    import logging
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    engine = UptrendEngineV4()
    updated = engine.run()
    logger.info("Uptrend Engine v4 updated %d positions", updated)


if __name__ == "__main__":
    main()

