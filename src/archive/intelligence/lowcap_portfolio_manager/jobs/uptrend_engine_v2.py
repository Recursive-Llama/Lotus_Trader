from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client  # type: ignore


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Global constants (aligned with SM_UPTREND.MD)
class Constants:
    """Centralized constants for uptrend engine."""
    # ADX floor
    ADX_FLOOR = 18.0
    
    # Sigmoid scales (k parameters)
    S1_CURVATURE_K = 0.0008
    S1_COMP_INV_K = 0.0015
    S1_EXPANSION_K = 0.3
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
    
    # Hysteresis thresholds
    HYSTERESIS_ON_THRESHOLD = 0.70
    HYSTERESIS_OFF_THRESHOLD = 0.60
    HYSTERESIS_ON_BARS = 3
    HYSTERESIS_OFF_BARS = 3
    
    # Bounce window (bars)
    BOUNCE_WINDOW_BARS = 6


class UptrendEngineV2:
    """Uptrend Engine v2 aligned with SM_UPTREND.MD.

    Responsibilities:
    - Read geometry (hourly SR map) and TA (1h indicators) from features
    - Detect S1 breakout (band-based), cache S1 artifacts
    - Manage S2 dynamic S/R supports (support_persistence, step-down/reclaim)
    - Compute S3 regime scores (OX/DX/EDX) and emit unified payload
    - Write live snapshot to features.uptrend_engine and emit events (to be added)
    - Append scores history (scores_log) (to be added)
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

    # --------------- Geometry/TA readers ---------------
    def _read_sr_levels(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        geom = features.get("geometry") or {}
        levels = ((geom.get("levels") or {}).get("sr_levels") or [])
        return list(levels)

    def _read_ta(self, features: Dict[str, Any]) -> Dict[str, Any]:
        return features.get("ta") or {}

    # --------------- Geometry helpers ---------------
    def _select_last_support_below_breakout(self, sr_levels: List[Dict[str, Any]], ohlc_rows: List[Dict[str, Any]], breakout_price: float) -> float:
        """Select highest S/R < breakout_price respected in last ~30 bars; fallback to swing low."""
        try:
            closes = [float(r.get("close_native") or 0.0) for r in ohlc_rows[-30:]]
            lows = [float(r.get("low_native") or 0.0) for r in ohlc_rows[-30:]]
        except Exception:
            closes, lows = [], []
        candidates: List[float] = []
        for lvl in sr_levels:
            try:
                p = float(lvl.get("price_native_raw") or lvl.get("price") or 0.0)
            except Exception:
                p = 0.0
            if 0.0 < p < breakout_price:
                candidates.append(p)
        candidates.sort(reverse=True)
        def respected(level: float) -> bool:
            if not closes:
                return False
            px = closes[-1] if closes else level
            halo = 0.03 * max(px, level)
            close_cnt = sum(1 for c in closes if c >= level)
            wick_cnt = sum(1 for lo, c in zip(lows, closes) if lo <= (level + halo) and c >= level)
            return (close_cnt >= 3) or (wick_cnt >= 2)
        for level in candidates:
            if respected(level):
                return level
        if lows:
            return min(lows)
        return 0.0

    def _check_s1_fakeout(self, contract: str, chain: str, features: Dict[str, Any]) -> bool:
        meta = dict(features.get("uptrend_engine_meta") or {})
        s1 = dict(meta.get("s1") or {})
        if not s1:
            return False
        ta = self._read_ta(features)
        slopes = (ta.get("ema_slopes") or {})
        last = self._latest_close_1h(contract, chain)
        px = float(last.get("close") or 0.0)
        last_support = float(s1.get("last_support_below_breakout") or 0.0)
        structural_failure = (last_support > 0.0 and px < last_support)
        ema60_slope = float(slopes.get("ema60_slope") or 0.0)
        ema144_slope = float(slopes.get("ema144_slope") or 0.0)
        d_ema60_slope = float(slopes.get("d_ema60_slope") or 0.0)
        flow_reversal = ((ema60_slope < 0.0 and ema144_slope < 0.0) or (d_ema60_slope < 0.0))
        breakout_ts = str(s1.get("breakout_ts") or "")
        avwap_slope_10 = 0.0
        consecutive_below = 0
        if breakout_ts:
            try:
                av = self._compute_avwap_since(contract, chain, breakout_ts)
                avwap = float(av.get("avwap") or 0.0)
                avwap_slope_10 = float(av.get("avwap_slope_10") or 0.0)
                recent = self._fetch_recent_ohlc(contract, chain, limit=5)
                for r in reversed(recent[-3:]):
                    c = float(r.get("close_native") or 0.0)
                    if avwap > 0.0 and c < avwap:
                        consecutive_below += 1
                consecutive_below = min(consecutive_below, 3)
            except Exception:
                pass
        conviction_collapse = (avwap_slope_10 < 0.0) or (consecutive_below >= 3)
        votes = sum(1 for cond in [structural_failure, flow_reversal, conviction_collapse] if cond)
        return votes >= 2

    # --------------- Hysteresis tracking ---------------
    def _update_hysteresis(self, features: Dict[str, Any], flag_name: str, current_value: float) -> bool:
        """Update hysteresis state for a flag. Returns True if flag should be ON, False if OFF.
        
        Args:
            features: Features dict (will be mutated to persist hysteresis state)
            flag_name: Name of the flag (e.g., 'trend_healthy', 'can_still_enter')
            current_value: Current score/value to check against thresholds
            
        Returns:
            True if flag should be ON, False if OFF
        """
        meta = dict(features.get("uptrend_engine_meta") or {})
        hyst = dict(meta.get("hysteresis") or {})
        flag_hyst = dict(hyst.get(flag_name) or {})
        
        on_count = int(flag_hyst.get("on_count") or 0)
        off_count = int(flag_hyst.get("off_count") or 0)
        current_state = bool(flag_hyst.get("active") or False)
        
        if current_value >= Constants.HYSTERESIS_ON_THRESHOLD:
            on_count += 1
            off_count = 0
        elif current_value < Constants.HYSTERESIS_OFF_THRESHOLD:
            off_count += 1
            on_count = 0
        else:
            # In dead zone, maintain current count but don't increment
            pass
        
        # Update state based on counts
        if on_count >= Constants.HYSTERESIS_ON_BARS:
            current_state = True
        elif off_count >= Constants.HYSTERESIS_OFF_BARS:
            current_state = False
        
        # Persist
        flag_hyst.update({
            "active": current_state,
            "on_count": on_count,
            "off_count": off_count,
            "last_value": current_value,
        })
        hyst[flag_name] = flag_hyst
        meta["hysteresis"] = hyst
        features["uptrend_engine_meta"] = meta
        
        return current_state

    # --------------- S0 compression_index and baseline storage ---------------
    def _compute_s0_compression_and_baselines(self, contract: str, chain: str, ta: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
        """Compute S0 compression_index and update baselines (continuous during S0).
        
        Per spec lines 136-160: compression_index blends ATR, band separations, and ADX.
        Baselines are updated every bar during S0, then frozen at S1 transition.
        """
        ema = ta.get("ema") or {}
        sep = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        mom = ta.get("momentum") or {}
        slopes = ta.get("ema_slopes") or {}
        
        import math
        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))
        
        # Get values
        ema50 = float(ema.get("ema50_1h") or 0.0)
        atr_1h = float(atr.get("atr_1h") or 0.0)
        atr_norm = atr_1h / max(ema50, 1e-9) if ema50 > 0 else 0.0
        
        # Compute ATR_norm_slope via linear regression over N=24 bars (per spec: slopes computed over ΔN bars)
        # Fetch recent OHLC to compute ATR_norm history
        atr_norm_slope = 0.0
        if ema50 > 0:
            try:
                # Fetch last 24 bars for ATR_norm slope computation
                rows = self._fetch_recent_ohlc(contract, chain, limit=30)  # Get a few extra for safety
                if len(rows) >= 24:
                    # Compute ATR for each bar (simple approximation: use high-low range as ATR proxy)
                    # Note: Ideally we'd have historical ATR values, but this approximation should work
                    # for slope detection since we care about trend direction, not exact magnitude
                    atr_norms: List[float] = []
                    for i in range(len(rows) - 24, len(rows)):
                        r = rows[i]
                        h = float(r.get("high_native") or 0.0)
                        l = float(r.get("low_native") or 0.0)
                        # Use high-low as ATR approximation (ATR ≈ high-low for volatile moves)
                        # For more accuracy, we could fetch actual historical ATR if available
                        bar_atr = h - l if h > l else 0.0
                        bar_atr_norm = bar_atr / max(ema50, 1e-9) if ema50 > 0 else 0.0
                        atr_norms.append(bar_atr_norm)
                    
                    # Linear regression: slope over last 24 bars
                    # x = 0..23 (bar index), y = atr_norm values
                    if len(atr_norms) == 24:
                        import statistics as _stats
                        xs = list(range(24))
                        x_mean = _stats.fmean(xs)
                        y_mean = _stats.fmean(atr_norms)
                        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, atr_norms))
                        den = sum((x - x_mean) ** 2 for x in xs) or 1.0
                        atr_norm_slope = num / den  # Slope per bar (negative during compression)
            except Exception:
                # Fallback: use simple comparison if regression fails
                atr_mean_20 = float(atr.get("atr_mean_20") or atr_1h)
                if atr_mean_20 > 0:
                    recent_mean_norm = atr_mean_20 / max(ema50, 1e-9)
                    atr_norm_slope = (atr_norm - recent_mean_norm) / max(recent_mean_norm, 1e-9) if recent_mean_norm > 0 else 0.0
        
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        adx_slope = float(mom.get("adx_slope_10") or 0.0)
        
        # Compression index per spec (k_atr=0.05, k_sep=0.0015, k_adx=0.2)
        k_atr = 0.05
        k_sep = 0.0015
        k_adx = 0.2
        
        compression_index = (
            0.40 * sigmoid(-atr_norm_slope / k_atr, 1.0) +
            0.30 * sigmoid(-dsep_fast / k_sep, 1.0) +
            0.20 * sigmoid(-dsep_mid / k_sep, 1.0) +
            0.10 * sigmoid(-adx_slope / k_adx, 1.0)
        )
        compression_index = max(0.0, min(1.0, compression_index))
        
        # Baselines to store
        sep_fast = float(sep.get("sep_fast") or 0.0)
        sep_mid = float(sep.get("sep_mid") or 0.0)
        adx_level = float(mom.get("adx_1h") or Constants.ADX_FLOOR)
        
        baselines = {
            "atr_norm_baseline": atr_norm,
            "sep_fast_start": sep_fast,
            "sep_mid_start": sep_mid,
            "adx_baseline": adx_level,
            "compression_index": compression_index,
        }
        
        # Update S0 meta (continuous update during S0)
        meta = dict(features.get("uptrend_engine_meta") or {})
        meta["s0"] = baselines
        features["uptrend_engine_meta"] = meta
        
        return {
            "compression_index": compression_index,
            "baselines": baselines,
            "atr_norm_slope": atr_norm_slope,
            "dsep_fast": dsep_fast,
            "dsep_mid": dsep_mid,
        }

    # --------------- S1 detection (scaffold) ---------------
    def _detect_s1_breakout(self, ta: Dict[str, Any]) -> Dict[str, Any]:
        """Band-based S1 breakout detection (minimal viable logic).

        Conditions (light-weight initial version):
        - ema20_slope > 0
        - dsep_fast_5 > 0
        - ATR_norm rising vs short mean (atr_1h > atr_mean_20)
        - vo_z_cluster_1h == True
        """
        ema_slopes = ta.get("ema_slopes") or {}
        seps = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        vol = ta.get("volume") or {}

        ema20_slope = float(ema_slopes.get("ema20_slope") or 0.0)
        dsep_fast_5 = float(seps.get("dsep_fast_5") or 0.0)
        atr_1h = float(atr.get("atr_1h") or 0.0)
        atr_mean_20 = float(atr.get("atr_mean_20") or atr_1h)
        vo_cluster = bool(vol.get("vo_z_cluster_1h") or False)

        breakout = (ema20_slope > 0.0) and (dsep_fast_5 > 0.0) and (atr_1h > atr_mean_20) and vo_cluster
        return {"breakout": breakout}

    def _compute_s1_scores(self, ta: Dict[str, Any], sr_flip_score: float, last_close: float) -> Dict[str, float]:
        """Compute S1 sub-scores and breakout_strength per SM spec (simplified with available TA)."""
        ema = ta.get("ema") or {}
        slopes = ta.get("ema_slopes") or {}
        sep = ta.get("separations") or {}
        atr = ta.get("atr") or {}
        vol = ta.get("volume") or {}
        mom = ta.get("momentum") or {}

        import math

        def sigmoid(x: float, k: float = 1.0) -> float:
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))

        # Flow flip integrity
        ema20_slope = float(slopes.get("ema20_slope") or 0.0)
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        ema60 = float(ema.get("ema60_1h") or 0.0)
        price_flag = 1.0 if (last_close >= ema60 and ema60 > 0.0) else 0.0
        curvature = sigmoid(ema20_slope / Constants.S1_CURVATURE_K, 1.0)
        comp_inv = sigmoid(dsep_fast / Constants.S1_COMP_INV_K, 1.0)
        flow_flip_integrity = 0.50 * curvature + 0.35 * comp_inv + 0.15 * price_flag

        # Expansion quality vs S0 baselines
        atr_1h = float(atr.get("atr_1h") or 0.0)
        ema50 = float(ema.get("ema50_1h") or 0.0)
        atr_norm_now = atr_1h / max(ema50, 1e-9) if ema50 > 0 else 0.0
        # fallbacks for baselines: use atr_mean_20 and current sep_fast as proxies if not present
        atr_mean_20 = float(atr.get("atr_mean_20") or atr_1h)
        atr_norm_baseline = atr_mean_20 / max(ema50, 1e-9) if ema50 > 0 else atr_norm_now
        sep_fast_now = float(sep.get("sep_fast") or 0.0)
        sep_fast_start = sep_fast_now  # if unknown, neutralize delta
        # Improvements if baseline exists in meta will be applied when storing
        atr_term = sigmoid((atr_norm_now - atr_norm_baseline) / max(abs(atr_norm_baseline), 1e-9), Constants.S1_EXPANSION_K)
        sep_term = sigmoid((sep_fast_now - sep_fast_start) / max(abs(sep_fast_start) if sep_fast_start != 0 else 1.0, 1.0), Constants.S1_EXPANSION_K)
        expansion_quality = max(0.0, min(1.0, 0.5 * (atr_term + sep_term)))

        # Volume cluster
        vo_z_1h = float(vol.get("vo_z_1h") or 0.0)
        vo_cluster = bool(vol.get("vo_z_cluster_1h") or False)
        volume_cluster = 1.0 if vo_cluster else max(0.0, min(1.0, vo_z_1h / 6.0))

        # Momentum drive (with ADX floor)
        rsi_slope_10 = float(mom.get("rsi_slope_10") or 0.0)
        adx_level = float(mom.get("adx_1h") or 0.0)
        adx_slope_10 = float(mom.get("adx_slope_10") or 0.0)
        # Apply ADX floor: only use slope if ADX is above floor
        adx_effective = max(adx_level, Constants.ADX_FLOOR)
        rsi_term = sigmoid(rsi_slope_10 / Constants.S3_RSI_K, 1.0)
        adx_term = sigmoid(adx_slope_10 / Constants.S3_ADX_K, 1.0) if adx_level >= Constants.ADX_FLOOR else 0.0
        momentum_drive = 0.6 * rsi_term + 0.4 * adx_term

        breakout_strength_base = (
            0.30 * flow_flip_integrity + 0.25 * expansion_quality + 0.20 * volume_cluster + 0.15 * momentum_drive + 0.10 * max(0.0, min(1.0, sr_flip_score))
        )

        return {
            "flow_flip_integrity": max(0.0, min(1.0, flow_flip_integrity)),
            "expansion_quality": max(0.0, min(1.0, expansion_quality)),
            "volume_cluster": max(0.0, min(1.0, volume_cluster)),
            "momentum_drive": max(0.0, min(1.0, momentum_drive)),
            "breakout_strength_base": max(0.0, min(1.0, breakout_strength_base)),
        }

    def _cache_s1_artifacts(self, sr_levels: List[Dict[str, Any]], px_breakout: float, px_prev_close: float) -> Dict[str, Any]:
        """Derive base_sr_level and (placeholder) flipped_sr_levels at S1 time.
        - base_sr_level: highest SR < breakout price
        - flipped_sr_levels: SRs at/under breakout considered flipped (placeholder approach)
        - sr_flip_score: normalized sum of flipped level strengths
        """
        base_sr = None
        for lvl in sr_levels:
            try:
                price = float(lvl.get("price_native_raw") or lvl.get("price") or 0.0)
            except Exception:
                price = 0.0
            if price < px_breakout:
                if base_sr is None or float(base_sr.get("price_native_raw") or base_sr.get("price") or 0.0) < price:
                    base_sr = lvl
        # Collect flipped levels: prev_close < level <= breakout (sorted desc)
        flipped_raw: List[Dict[str, Any]] = []
        for lvl in sr_levels:
            try:
                price = float(lvl.get("price_native_raw") or lvl.get("price") or 0.0)
            except Exception:
                price = 0.0
            if (price > px_prev_close) and (price <= px_breakout) and price > 0:
                flipped_raw.append(lvl)
        flipped_raw.sort(key=lambda x: float(x.get("price_native_raw") or x.get("price") or 0.0), reverse=True)
        # Normalize level score from strength/confidence
        def _norm_score(l: Dict[str, Any]) -> float:
            try:
                strength = float(l.get("strength") or 0.0)
            except Exception:
                strength = 0.0
            try:
                confidence = float(l.get("confidence") or 0.0)
            except Exception:
                confidence = 0.0
            s_norm = min(1.0, strength / 20.0)  # tune later
            c_norm = max(0.0, min(1.0, confidence))
            return max(0.0, min(1.0, 0.5 * s_norm + 0.5 * c_norm))
        flipped: List[Dict[str, Any]] = []
        sr_flip_total = 0.0
        for order_idx, lvl in enumerate(flipped_raw, start=1):
            price = float(lvl.get("price_native_raw") or lvl.get("price") or 0.0)
            score = _norm_score(lvl)
            sr_flip_total += score
            flipped.append({
                "id": lvl.get("id"),
                "level": price,
                "score": score,
                "order": order_idx,
                "flipped_at": _now_iso(),
            })
        # sr_flip_score via sigmoid on total
        import math
        scale = 5.0  # tune later based on typical flipped counts/scores
        sr_flip_score = 1.0 / (1.0 + math.exp(- (sr_flip_total / scale))) if scale > 0 else min(1.0, sr_flip_total)
        return {
            "base_sr_level": (float(base_sr.get("price_native_raw") or base_sr.get("price") or 0.0) if base_sr else 0.0),
            "flipped_sr_levels": flipped,
            "sr_flip_score": sr_flip_score,
        }

    # --------------- Unified payload builder (scaffold) ---------------
    def _build_payload(self, state: str, features: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
        ta = self._read_ta(features)
        ema = (ta.get("ema") or {})
        payload: Dict[str, Any] = {
            "state": state,
            "timeframe": "1h",
            "t0": _now_iso(),
            "flag": extra.get("flag", {}),
            "scores": extra.get("scores", {}),
            "levels": {
                "ema20": float(ema.get("ema20_1h") or 0.0),
                "ema60": float(ema.get("ema60_1h") or 0.0),
                "ema144": float(ema.get("ema144_1h") or 0.0),
                "ema250": float(ema.get("ema250_1h") or 0.0),
                "ema333": float(ema.get("ema333_1h") or 0.0),
            },
            "diagnostics": extra.get("diagnostics", {}),
            "meta": {"updated_at": _now_iso()},
        }
        # Attach SR if provided
        for k in ("base_sr_level", "flipped_sr_levels"):
            if k in extra:
                payload.setdefault("levels", {})[k] = extra[k]
        return payload

    # --------------- S2 dynamic S/R manager (initial) ---------------
    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
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

    def _last_two_closes_1h(self, contract: str, chain: str) -> List[Dict[str, Any]]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .order("timestamp", desc=True)
            .limit(2)
            .execute()
            .data
            or []
        )
        return list(rows)

    def _fetch_ohlc_since(self, contract: str, chain: str, since_iso: str) -> List[Dict[str, Any]]:
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

    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 60) -> List[Dict[str, Any]]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume_native")
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

    def _compute_avwap_since(self, contract: str, chain: str, since_iso: str) -> Dict[str, float]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, volume_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .gte("timestamp", since_iso)
            .order("timestamp")
            .execute()
            .data
            or []
        )
        if not rows:
            return {"avwap": 0.0, "avwap_slope_10": 0.0}
        import statistics as _stats
        pv_sum = 0.0
        v_sum = 0.0
        avwaps: List[float] = []
        for r in rows:
            c = float(r.get("close_native") or 0.0)
            v = float(r.get("volume_native") or 0.0)
            v = max(0.0, v)
            pv_sum += c * v
            v_sum += v
            avwaps.append(pv_sum / v_sum if v_sum > 0 else c)
        avwap = avwaps[-1]
        tail = avwaps[-10:] if len(avwaps) >= 10 else avwaps
        n = len(tail)
        if n >= 2 and avwap > 0:
            xs = list(range(n))
            x_mean = _stats.fmean(xs)
            y_mean = _stats.fmean(tail)
            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, tail))
            den = sum((x - x_mean) ** 2 for x in xs) or 1.0
            slope = num / den
            slope_norm = slope / avwap
        else:
            slope_norm = 0.0
        return {"avwap": avwap, "avwap_slope_10": slope_norm}

    def _s2_manage(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        ta = self._read_ta(features)
        atr_block = ta.get("atr") or {}
        ema_block = ta.get("ema") or {}
        slope_block = ta.get("ema_slopes") or {}
        atr_1h = float(atr_block.get("atr_1h") or 0.0)
        # Read S1 artifacts from meta
        meta = dict(features.get("uptrend_engine_meta") or {})
        s1meta = dict(meta.get("s1") or {})
        flipped = list(s1meta.get("flipped_sr_levels") or [])
        base_sr = float(s1meta.get("base_sr_level") or 0.0)
        if base_sr <= 0.0 and not flipped:
            return {"active": False}

        # Build ordered SR list (price desc) from flipped then base
        sr_list: List[float] = [float(f.get("level") or 0.0) for f in flipped if float(f.get("level") or 0.0) > 0.0]
        if base_sr > 0.0:
            sr_list.append(base_sr)

        ue_meta_s2 = dict(meta.get("s2") or {})
        current_sr = float(ue_meta_s2.get("current_sr") or 0.0)
        t0_ts = str(ue_meta_s2.get("t0_ts") or "")

        last = self._latest_close_1h(contract, chain)
        px = last["close"]
        low = last["low"]
        halo = max(0.5 * atr_1h, 0.03 * px) if px > 0 else 0.0

        # Activation: set current_sr to highest flipped first
        if current_sr <= 0.0 and sr_list:
            candidate = sr_list[0]
            if (low <= candidate + halo) and (px >= candidate):
                current_sr = candidate
                t0_ts = last.get("ts") or _now_iso()
                ue_meta_s2 = {"current_sr": current_sr, "t0_ts": t0_ts}
                meta["s2"] = ue_meta_s2
                features["uptrend_engine_meta"] = meta

        # Step-down if lost current_sr
        if current_sr > 0.0 and px < current_sr:
            try:
                idx = sr_list.index(current_sr)
            except ValueError:
                idx = 0
            if idx + 1 < len(sr_list):
                current_sr = sr_list[idx + 1]
                ue_meta_s2["current_sr"] = current_sr
                # mark dent pending for multiplier application this run
                ue_meta_s2["dent_pending"] = True
                meta["s2"] = ue_meta_s2
                features["uptrend_engine_meta"] = meta

        # Reclaim higher SR if possible
        if current_sr > 0.0:
            try:
                idx = sr_list.index(current_sr)
            except ValueError:
                idx = 0
            if idx > 0 and px >= sr_list[idx - 1]:
                current_sr = sr_list[idx - 1]
                ue_meta_s2["current_sr"] = current_sr
                ue_meta_s2["reclaim_boost_pending"] = True
                meta["s2"] = ue_meta_s2
                features["uptrend_engine_meta"] = meta

        # Compute support_persistence since t0
        support_persistence = 0.0
        reaction_quality = 0.0
        close_persistence = 0.0
        absorption_wicks = 0.0
        if current_sr > 0.0 and t0_ts:
            rows = self._fetch_ohlc_since(contract, chain, t0_ts)
            closes = [float(r.get("close_native") or 0.0) for r in rows]
            lows = [float(r.get("low_native") or 0.0) for r in rows]
            highs = [float(r.get("high_native") or 0.0) for r in rows]
            # close_persistence
            cnt_closes = sum(1 for v in closes if v >= current_sr)
            import math
            close_persistence = 1.0 - math.exp(-(cnt_closes / 6.0))
            # absorption_wicks
            wick_cnt = sum(1 for lo, cl in zip(lows, closes) if lo < current_sr and cl >= current_sr)
            absorption_wicks = 1.0 - math.exp(-(wick_cnt / 2.0))
            # reaction_quality
            if highs:
                bounce_atr = (max(highs) - current_sr) / max(atr_1h, 1e-9)
                reaction_quality = min(1.0, bounce_atr / 1.0)
            touch_confirm = 1.0 if (low <= current_sr + halo and px >= current_sr) else 0.0
            support_persistence = 0.25 * touch_confirm + 0.20 * reaction_quality + 0.40 * close_persistence + 0.15 * absorption_wicks

        # EMA proximity boost to persistence (+5% if near EMA60/144 within 0.5 ATR)
        ema60_val = float(ema_block.get("ema60_1h") or 0.0)
        ema144_val = float(ema_block.get("ema144_1h") or 0.0)
        near_ema = False
        if current_sr > 0.0 and atr_1h > 0.0:
            if ema60_val > 0.0 and abs(current_sr - ema60_val) <= 0.5 * atr_1h:
                near_ema = True
            if ema144_val > 0.0 and abs(current_sr - ema144_val) <= 0.5 * atr_1h:
                near_ema = True
        if near_ema:
            support_persistence *= 1.05

        # Compute TI/TS per spec (simplified weighting per doc)
        # ema_alignment: heavy weight to slow foundation (144/250/333)
        def _clip01(x: float) -> float:
            return max(0.0, min(1.0, x))
        ema60_slope = float(slope_block.get("ema60_slope") or 0.0)
        ema144_slope = float(slope_block.get("ema144_slope") or 0.0)
        ema250_slope = float(slope_block.get("ema250_slope") or 0.0)
        ema333_slope = float(slope_block.get("ema333_slope") or 0.0)
        d_ema60_slope = float(slope_block.get("d_ema60_slope") or 0.0)
        d_ema144_slope = float(slope_block.get("d_ema144_slope") or 0.0)
        d_ema250_slope = float(slope_block.get("d_ema250_slope") or 0.0)
        d_ema333_slope = float(slope_block.get("d_ema333_slope") or 0.0)
        # slow_positive: fraction of slow slopes ≥ 0
        slow_pos_count = sum(1 for v in [ema144_slope, ema250_slope, ema333_slope] if v >= 0.0)
        slow_positive = slow_pos_count / 3.0
        # slow_acceleration: average of positive acceleration signals (normalize lightly)
        slow_accel = sum(1.0 for v in [d_ema144_slope, d_ema250_slope, d_ema333_slope] if v > 0.0) / 3.0
        # mid help (ema60 slope)
        mid_help = 1.0 if ema60_slope >= 0.0 else 0.0
        # fast>mid ordering
        try:
            ema20_val = float(ema_block.get("ema20_1h") or 0.0)
            ema60_val = float(ema_block.get("ema60_1h") or 0.0)
            fast_gt_mid = 1.0 if ema20_val > ema60_val else 0.0
            sep_fast = float((ta.get("separations") or {}).get("sep_fast") or 0.0)
        except Exception:
            fast_gt_mid = 0.0
            sep_fast = 0.0
        # ema_alignment composite
        ema_alignment = (
            0.50 * _clip01(0.30 * slow_positive + 0.40 * slow_accel + 0.30 * slow_positive) +
            0.15 * mid_help +
            0.20 * fast_gt_mid +
            0.15 * _clip01(sep_fast)
        )
        # volatility_coherence: ATR reduction since breakout not available here; approximate via atr_mean_20
        atr_mean_20 = float(atr_block.get("atr_mean_20") or atr_1h)
        red_ratio = (atr_1h - atr_mean_20) / max(atr_mean_20, 1e-9)
        # Map negative red_ratio (ATR below mean) to higher coherence
        import math
        volatility_coherence = 1.0 / (1.0 + math.exp((red_ratio) / 0.3))
        # TI
        trend_integrity = 0.55 * support_persistence + 0.35 * ema_alignment + 0.10 * volatility_coherence
        # TS (with ADX floor)
        mom = ta.get("momentum") or {}
        rsi_slope_10 = float(mom.get("rsi_slope_10") or 0.0)
        adx_level = float(mom.get("adx_1h") or 0.0)
        adx_slope_10 = float(mom.get("adx_slope_10") or 0.0)
        # Apply ADX floor: only use slope if ADX is above floor
        rsi_term = 1.0 / (1.0 + math.exp(-rsi_slope_10 / Constants.S3_RSI_K))
        adx_term = 1.0 / (1.0 + math.exp(-adx_slope_10 / Constants.S3_ADX_K)) if adx_level >= Constants.ADX_FLOOR else 0.0
        trend_strength = 0.6 * rsi_term + 0.4 * adx_term

        # Apply dents/boosts based on step-down/reclaim flags
        if bool(ue_meta_s2.get("dent_pending")):
            trend_integrity *= 0.4
            trend_strength *= 0.6
            ue_meta_s2.pop("dent_pending", None)
            meta["s2"] = ue_meta_s2
            features["uptrend_engine_meta"] = meta
        if bool(ue_meta_s2.get("reclaim_boost_pending")):
            trend_integrity = min(1.0, trend_integrity * 1.3)
            trend_strength = min(1.0, trend_strength * 1.6)
            ue_meta_s2.pop("reclaim_boost_pending", None)
            meta["s2"] = ue_meta_s2
            features["uptrend_engine_meta"] = meta

        # Tier boosts: +10% per tier down, +30% at base
        tier_boost = 0.0
        if current_sr > 0.0 and sr_list:
            try:
                idx = sr_list.index(current_sr)
            except ValueError:
                idx = 0
            is_base = (idx == len(sr_list) - 1 and base_sr > 0.0 and current_sr == base_sr)
            if is_base:
                tier_boost = 0.30
            else:
                # idx 0 = highest flipped; deeper tiers have larger idx
                if idx > 0:
                    tier_boost = 0.10 * idx
        if tier_boost > 0.0:
            trend_integrity = min(1.0, trend_integrity * (1.0 + tier_boost))
            trend_strength = min(1.0, trend_strength * (1.0 + tier_boost))

        # uptrend_confirmed: simplified proxy (no monotonic TS series), use thresholds + reclaim score
        def _sr_reclaim_score(contract: str, chain: str, since_iso: str) -> float:
            try:
                rows = (
                    self.sb.table("lowcap_sr_levels")
                    .select("level_score, reclaimed_at")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .gte("reclaimed_at", since_iso)
                    .eq("status", "reclaimed")
                    .execute()
                    .data
                    or []
                )
                return sum(float(r.get("level_score") or 0.0) for r in rows)
            except Exception:
                return 0.0

        sr_reclaim_score = _sr_reclaim_score(contract, chain, t0_ts) if (t0_ts and current_sr > 0.0) else 0.0
        uptrend_confirmed = (
            support_persistence >= 0.6 and reaction_quality >= 0.3 and (rsi_slope_10 > 0.0 and adx_slope_10 > 0.0) and sr_reclaim_score >= 30.0
        )

        # Flags
        uptrend_holding = current_sr > 0.0 and px >= current_sr
        return {
            "active": current_sr > 0.0,
            "current_sr": current_sr,
            "t0_ts": t0_ts,
            "halo": halo,
            "scores": {
                "support_persistence": support_persistence,
                "reaction_quality": reaction_quality,
                "close_persistence": close_persistence,
                "absorption_wicks": absorption_wicks,
                "trend_integrity": _clip01(trend_integrity),
                "trend_strength": _clip01(trend_strength),
                "sr_reclaim_score": sr_reclaim_score,
            },
            "flags": {"uptrend_holding": uptrend_holding, "uptrend_confirmed": uptrend_confirmed},
            "features": features,
        }

    # --------------- S3 OX/DX/EDX calculators (initial) ---------------
    def _compute_s3_scores(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
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
        vo_cluster = bool(vol.get("vo_z_cluster_1h") or False)
        ema20_slope = float(slopes.get("ema20_slope") or 0.0)
        d_ema144_slope = float(slopes.get("d_ema144_slope") or 0.0)

        def sigmoid(x: float, k: float = 1.0) -> float:
            import math
            return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))

        # EDX (expanded composite): slow curvature + structure failure + participation decay + volatility disorder + geometry rollover
        ema144_slope = float(slopes.get("ema144_slope") or 0.0)
        ema250_slope = float(slopes.get("ema250_slope") or 0.0)
        ema333_slope = float(slopes.get("ema333_slope") or 0.0)
        slow_down = sigmoid(-(ema250_slope) / Constants.S3_EDX_SLOW_K, 1.0) * 0.5 + sigmoid(-(ema333_slope) / Constants.S3_EDX_SLOW_333_K, 1.0) * 0.5

        # Structure failure approximations over recent window
        rows = self._fetch_recent_ohlc(contract, chain, limit=50)
        closes = [float(r.get("close_native") or 0.0) for r in rows]
        lows = [float(r.get("low_native") or 0.0) for r in rows]
        # closes_below_ema60 ratio (soft structural decay)
        ema60_val = float(ema.get("ema60_1h") or 0.0)
        below_mid_ratio = 0.0
        if ema60_val > 0.0 and closes:
            below_mid_ratio = sum(1 for c in closes if c < ema60_val) / float(len(closes) or 1)
        # lower-low fraction
        ll_ratio = 0.0
        if len(lows) >= 2:
            ll_ratio = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i - 1]) / float(len(lows) - 1)
        struct = 0.5 * sigmoid((ll_ratio - 0.5) / 0.2, 1.0) + 0.5 * sigmoid((below_mid_ratio - 0.4) / 0.2, 1.0)

        # Participation decay
        part_decay = sigmoid(-(vo_z_1h) / 1.0, 1.0)

        # Volatility disorder: ATR asymmetry up vs down proxy via TR
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
        import statistics as _stats
        up_avg = _stats.fmean(ups) if ups else (sum(trs) / len(trs) if trs else 0.0)
        down_avg = _stats.fmean(downs) if downs else (sum(trs) / len(trs) if trs else 0.0)
        asym = 0.0
        if up_avg > 0.0:
            asym = sigmoid(((down_avg / up_avg) - 1.0) / 0.2, 1.0)

        # Geometry rollover: sep rolls negative
        dsep_fast = float(sep.get("dsep_fast_5") or 0.0)
        dsep_mid = float(sep.get("dsep_mid_5") or 0.0)
        geom_roll = 0.6 * sigmoid(-(dsep_mid) / Constants.S3_EXP_MID_K, 1.0) + 0.4 * sigmoid(-(dsep_fast) / Constants.S3_EXP_FAST_K, 1.0)

        # Weighted composite per doc guidance
        edx_raw = 0.30 * slow_down + 0.25 * struct + 0.20 * part_decay + 0.15 * asym + 0.10 * geom_roll
        edx_raw = max(0.0, min(1.0, edx_raw))
        # Smooth EDX with simple EMA (span≈20) and reset on asset change
        meta = dict(features.get("uptrend_engine_meta") or {})
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
        features["uptrend_engine_meta"] = meta

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
        # EDX modulation (+33% max)
        edx_boost = max(0.0, min(0.5, edx - 0.5))
        ox = max(0.0, min(1.0, ox_base * (1.0 + 0.33 * edx_boost)))

        # DX: hallway 144→333, exhaustion/relief/curl
        if ema333 > ema144 and (ema333 - ema144) > 0 and px > 0:
            x = max(0.0, min(1.0, (px - ema144) / max((ema333 - ema144), 1e-9)))
        else:
            x = 1.0 if px <= ema144 else 0.0
        import math
        # Compression multiplier: narrower (ema333-ema144) vs historical proxy using last 50 lows
        band_width = max(ema333 - ema144, 1e-9)
        # Use relative width normalized by price to avoid scale issues
        comp_mult = sigmoid((0.03 - (band_width / max(px, 1e-9))) / 0.02, 1.0)  # narrower than ~3% of price boosts
        dx_location = math.exp(-3.0 * x) * (1.0 + 0.3 * comp_mult)  # deeper → higher; boost when compressed
        # Exhaustion: use negative VO_z proxy and recent slope improvement
        exhaustion = max(0.0, min(1.0, sigmoid(-vo_z_1h / 1.0, 1.0)))
        # Relief: ATR cooling + positive momentum slopes
        atr_relief = sigmoid(((atr_1h / max(atr_mean_20, 1e-9)) - 0.9) / 0.05, 1.0)
        rsi_slope_10 = float(mom.get("rsi_slope_10") or 0.0)
        adx_level = float(mom.get("adx_1h") or 0.0)
        adx_slope_10 = float(mom.get("adx_slope_10") or 0.0)
        # Apply ADX floor for relief term
        rsi_relief = sigmoid(rsi_slope_10 / Constants.S3_RSI_K, 1.0)
        adx_relief = sigmoid(adx_slope_10 / Constants.S3_ADX_K, 1.0) if adx_level >= Constants.ADX_FLOOR else 0.0
        mom_relief = 0.5 * rsi_relief + 0.5 * adx_relief
        relief = 0.5 * atr_relief + 0.5 * mom_relief
        curl = 1.0 if d_ema144_slope > 0.0 else 0.0
        dx_base = 0.45 * dx_location + 0.25 * exhaustion + 0.25 * relief + 0.05 * curl
        # EDX suppression (score, not gate)
        supp = max(0.0, min(0.4, edx - 0.6))
        dx = max(0.0, min(1.0, dx_base * (1.0 - 0.5 * supp)))

        # AVWAP (anchor at S1 breakout) for diagnostics
        breakout_meta = ((features.get("uptrend_engine_meta") or {}).get("s1") or {})
        breakout_ts = breakout_meta.get("breakout_ts")
        avwap_val = 0.0
        avwap_slope_10 = 0.0
        if breakout_ts:
            try:
                av = self._compute_avwap_since(contract, chain, breakout_ts)
                avwap_val = float(av.get("avwap") or 0.0)
                avwap_slope_10 = float(av.get("avwap_slope_10") or 0.0)
            except Exception:
                pass

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
                "avwap": avwap_val,
                "avwap_slope_10": avwap_slope_10,
            },
            "features": features,
        }

    # --------------- Main loop ---------------
    def run(self) -> int:
        now = datetime.now(timezone.utc)
        updated = 0
        positions = self._active_positions()
        for p in positions:
            try:
                pid = p.get("id")
                contract = p.get("token_contract")
                chain = p.get("token_chain")
                features = p.get("features") or {}
                prev_payload = dict(features.get("uptrend_engine") or {})
                prev_state = str(prev_payload.get("state") or "")

                sr_levels = self._read_sr_levels(features)
                ta = self._read_ta(features)
                if not sr_levels or not ta:
                    # Not enough inputs to compute engine state
                    continue

                # Bootstrap: If first run (no prev_state), determine initial state using window-based price vs EMA333 check
                if not prev_state or prev_state == "":
                    ema = ta.get("ema", {})
                    ema333 = float(ema.get("ema333_1h", 0.0))
                    
                    # If EMA333 not valid (0 or negative), default to S0
                    if ema333 <= 0:
                        # Default to S0 (will continue to normal S0 logic below)
                        pass
                    else:
                        # Window check: get last 10 bars and count how many have price < EMA333
                        try:
                            recent_rows = self._fetch_recent_ohlc(contract, chain, limit=10)
                            if len(recent_rows) >= 10:
                                below_count = 0
                                for r in recent_rows[-10:]:  # Last 10 bars
                                    px = float(r.get("close_native", 0.0))
                                    if px < ema333:
                                        below_count += 1
                                
                                # If 8+ out of 10 bars have price < EMA333 → S0 (downtrend)
                                if below_count >= 8:
                                    # Bootstrap to S0 (will continue to normal S0 logic below)
                                    pass
                                else:
                                    # Otherwise → S3 (uptrend or neutral)
                                    # Bootstrap to S3 (operating regime)
                                    s3 = self._compute_s3_scores(contract, chain, features)
                                    if s3:
                                        payload = self._build_payload("S3", features, {
                                            "scores": s3.get("scores", {}),
                                            "diagnostics": s3.get("diagnostics", {}),
                                        })
                                        payload["flags"] = s3.get("flags", {})
                                        # Add sr_context for S3
                                        try:
                                            atr_1h = float((ta.get("atr") or {}).get("atr_1h") or 0.0)
                                            last_px = float((ta.get("ema") or {}).get("ema20_1h") or 0.0)
                                            halo = max(0.5 * atr_1h, 0.03 * last_px) if last_px > 0 else 0.0
                                            # Get S/R levels from geometry
                                            flipped_sr = []
                                            for sr in sr_levels[:5]:  # Top 5
                                                price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                                                if price > 0:
                                                    flipped_sr.append({"level": price, "score": sr.get("strength", 10)})
                                            flipped_sr.sort(key=lambda x: float(x.get("level", 0.0)), reverse=True)
                                            base_sr = float(flipped_sr[-1].get("level", 0.0)) if flipped_sr else 0.0
                                            payload["sr_context"] = {
                                                "halo": halo,
                                                "base_sr_level": base_sr,
                                                "flipped_sr_levels": flipped_sr,
                                            }
                                        except Exception:
                                            payload["sr_context"] = {}
                                        features["uptrend_engine"] = payload
                                        new_features = dict(features)
                                        new_features["uptrend_engine"] = payload
                                        self._write_features(pid, new_features)
                                        updated += 1
                                        continue
                            # If not enough recent rows, default to S0
                        except Exception:
                            # If window check fails, default to S0
                            pass
                    
                    # Default to S0 (will continue to normal S0 logic below)

                # State transition logic: S0 → S1 → S2 → S3; S3 can only exit to S0 (never back to S1/S2)
                payload = None
                
                # S1 detection: ONLY from S0 (not from S3 - once in S3, breakout already happened)
                if prev_state in ("", "S0"):
                    s1 = self._detect_s1_breakout(ta)
                    if s1.get("breakout"):
                        # Use last two closes to determine breakout vs previous close
                        closes2 = self._last_two_closes_1h(contract, chain)
                        if len(closes2) >= 2:
                            px_breakout = float(closes2[0].get("close_native") or 0.0)
                            px_prev_close = float(closes2[1].get("close_native") or 0.0)
                        elif len(closes2) == 1:
                            px_breakout = float(closes2[0].get("close_native") or 0.0)
                            px_prev_close = px_breakout
                        else:
                            px_breakout = float((ta.get("ema") or {}).get("ema20_1h") or 0.0)
                            px_prev_close = px_breakout
                        s1_sr = self._cache_s1_artifacts(sr_levels, px_breakout, px_prev_close)
                        # Persist S1 artifacts to meta for S2 use
                        meta = dict(features.get("uptrend_engine_meta") or {})
                        # Freeze S0 baselines at S1 transition (per spec: baselines persist until fakeout or S2)
                        s0_baselines = dict(meta.get("s0") or {})
                        # If S0 baselines exist, use them; otherwise compute fallback
                        if not s0_baselines:
                            # Compute S0 baselines as fallback (shouldn't happen in normal flow)
                            s0_comp = self._compute_s0_compression_and_baselines(contract, chain, ta, features)
                            s0_baselines = s0_comp.get("baselines", {})
                        # Freeze: copy S0 baselines to S1 (these remain constant throughout S1)
                        # Also cache last_support_below_breakout from recent S0 window
                        try:
                            recent_rows = self._fetch_recent_ohlc(contract, chain, limit=50)
                            lsb = self._select_last_support_below_breakout(sr_levels, recent_rows, px_breakout)
                        except Exception:
                            lsb = float(s1_sr.get("base_sr_level") or 0.0)
                        # Get ATR at breakout for tracking
                        atr_1h_at_breakout = float((ta.get("atr") or {}).get("atr_1h") or 0.0)
                        ema50 = float((ta.get("ema") or {}).get("ema50_1h") or 0.0)
                        atr_norm_at_breakout = atr_1h_at_breakout / max(ema50, 1e-9) if ema50 > 0 else 0.0
                        
                        meta["s1"] = {
                            "base_sr_level": s1_sr.get("base_sr_level", 0.0),
                            "flipped_sr_levels": s1_sr.get("flipped_sr_levels", []),
                            "sr_flip_score": s1_sr.get("sr_flip_score", 0.0),
                            "breakout_price": px_breakout,
                            "breakout_ts": _now_iso(),
                            "breakout_high": px_breakout,  # Track highest price during S1
                            "atr_1h_at_breakout": atr_1h_at_breakout,
                            "atr_1h_peak": atr_1h_at_breakout,  # Track peak ATR during S1
                            "atr_norm_at_breakout": atr_norm_at_breakout,
                            # Frozen S0 baselines
                            "atr_norm_baseline": float(s0_baselines.get("atr_norm_baseline") or 0.0),
                            "sep_fast_start": float(s0_baselines.get("sep_fast_start") or 0.0),
                            "sep_mid_start": float(s0_baselines.get("sep_mid_start") or 0.0),
                            "adx_baseline": float(s0_baselines.get("adx_baseline") or Constants.ADX_FLOOR),
                            "s0_compression_index": float(s0_baselines.get("compression_index") or 0.5),
                            "last_support_below_breakout": float(lsb or 0.0),
                        }
                        features["uptrend_engine_meta"] = meta
                        # Compute S1 sub-scores
                        s1_scores = self._compute_s1_scores(ta, float(s1_sr.get("sr_flip_score", 0.0)), px_breakout)
                        bs_base = s1_scores.pop("breakout_strength_base", 0.0)
                        # Apply compression boost
                        b_boost = 0.85 + 0.15 * s0_compression_index
                        breakout_strength = max(0.0, min(1.0, bs_base * b_boost))
                        payload = self._build_payload("S1", features, {
                            "flag": {"breakout_confirmed": True},
                            **s1_sr,
                            "scores": {"sr_flip_score": s1_sr.get("sr_flip_score", 0.0), "breakout_strength": breakout_strength, **s1_scores},
                        })
                
                # S1 → S2 transition: Check if breakout finished (volatility cooling OR momentum slowing OR price pullback)
                if prev_state == "S1" and payload is None:
                    meta_s1 = dict(features.get("uptrend_engine_meta") or {})
                    s1_meta = dict(meta_s1.get("s1") or {})
                    if s1_meta:
                        # Get current values
                        last = self._latest_close_1h(contract, chain)
                        current_price = last["close"]
                        current_atr_1h = float((ta.get("atr") or {}).get("atr_1h") or 0.0)
                        ema50 = float((ta.get("ema") or {}).get("ema50_1h") or 0.0)
                        ema_slopes = ta.get("ema_slopes") or {}
                        seps = ta.get("separations") or {}
                        
                        # Track peak ATR and breakout high during S1
                        atr_1h_peak = float(s1_meta.get("atr_1h_peak") or current_atr_1h)
                        atr_1h_peak = max(atr_1h_peak, current_atr_1h)
                        breakout_high = float(s1_meta.get("breakout_high") or current_price)
                        breakout_high = max(breakout_high, current_price)
                        
                        # Update tracked values
                        s1_meta["atr_1h_peak"] = atr_1h_peak
                        s1_meta["breakout_high"] = breakout_high
                        meta_s1["s1"] = s1_meta
                        features["uptrend_engine_meta"] = meta_s1
                        
                        # Condition 1: ATR volatility cooling from peak (10% drop)
                        volatility_cooling = current_atr_1h < (atr_1h_peak * 0.90)
                        
                        # Condition 2: Short EMAs flattening (momentum slowing)
                        ema20_slope = float(ema_slopes.get("ema20_slope") or 0.0)
                        dsep_fast_5 = float(seps.get("dsep_fast_5") or 0.0)
                        # Normalize ema20_slope by ATR/price for volatility scaling
                        atr_pct = (current_atr_1h / max(current_price, 1e-9)) if current_price > 0 else 0.0
                        ema20_slope_norm = ema20_slope / max(atr_pct, 1e-9) if atr_pct > 0 else 0.0
                        momentum_slowed = (ema20_slope_norm < 0.1) or (dsep_fast_5 < 0.005)
                        
                        # Condition 3: Price pullback (6% minimum OR 1x ATR%, whichever is larger)
                        if breakout_high > 0 and current_price > 0:
                            pullback = (breakout_high - current_price) / breakout_high
                            atr_pct_of_price = (current_atr_1h / current_price) if current_price > 0 else 0.0
                            pullback_threshold = max(0.06, atr_pct_of_price * 1.0)  # 6% minimum OR 1x ATR%
                            price_pulled_back = pullback >= pullback_threshold
                        else:
                            price_pulled_back = False
                        
                        # Transition S1 → S2 if ANY condition is met
                        if volatility_cooling or momentum_slowed or price_pulled_back:
                            # Transition to S2 - create payload immediately (even if active=False)
                            # S2 state should exist as soon as breakout finishes, regardless of price touching S/R
                            s2 = self._s2_manage(contract, chain, features)
                            meta_ro = dict(features.get("uptrend_engine_meta") or {})
                            s1_ro = dict(meta_ro.get("s1") or {})
                            base_sr_level = s1_ro.get("base_sr_level", 0.0)
                            flipped_sr_levels = s1_ro.get("flipped_sr_levels", [])
                            payload = self._build_payload("S2", features, {
                                "flag": {"uptrend_holding": s2.get("flags", {}).get("uptrend_holding", False)},
                                "scores": s2.get("scores", {}),  # Still computes TI/TS even if active=False
                                "base_sr_level": base_sr_level,
                                "flipped_sr_levels": flipped_sr_levels,
                            })
                            payload.setdefault("supports", {})
                            payload["supports"].update({
                                "current_sr_level": s2.get("current_sr", 0.0),  # May be 0 if not active yet
                                "halo": s2.get("halo", 0.0),
                            })
                            # Update meta persisted earlier
                            features = s2.get("features", features)
                        else:
                            # Stay in S1 - breakout still happening
                            payload = self._build_payload("S1", features, {
                                "flag": {"breakout_confirmed": True},
                                "scores": prev_payload.get("scores", {}),
                            })
                            # Update features with tracked values
                            features["uptrend_engine_meta"] = meta_s1
                
                # S2 → S3 transition: ONLY from S2, requires price > EMA333 for 8+ of 10 candles + EMA slopes + momentum
                # NOTE: Must check BEFORE S2 stay check, otherwise S2 stay creates payload and this never runs
                if payload is None and prev_state == "S2":
                    # Check if we should transition to S3
                    ema = ta.get("ema", {})
                    ema333 = float(ema.get("ema333_1h") or 0.0)
                    slopes = ta.get("ema_slopes") or {}
                    mom = ta.get("momentum") or {}
                    
                    # Condition 1: Price > EMA333 for 8+ of last 10 candles (window check)
                    price_above_ema333 = False
                    if ema333 > 0:
                        try:
                            recent_rows = self._fetch_recent_ohlc(contract, chain, limit=10)
                            if len(recent_rows) >= 10:
                                above_count = 0
                                for r in recent_rows[-10:]:
                                    px = float(r.get("close_native") or 0.0)
                                    if px > ema333:
                                        above_count += 1
                                price_above_ema333 = above_count >= 8
                        except Exception:
                            pass
                    
                    # Condition 2: EMAs sloping up (2 out of 3 slow EMAs positive)
                    ema144_slope = float(slopes.get("ema144_slope") or 0.0)
                    ema250_slope = float(slopes.get("ema250_slope") or 0.0)
                    ema333_slope = float(slopes.get("ema333_slope") or 0.0)
                    slow_positive_count = sum(1 for s in [ema144_slope, ema250_slope, ema333_slope] if s >= 0.0)
                    ema_slopes_up = slow_positive_count >= 2  # 2 out of 3
                    
                    # Condition 3: Trend strength score (uses RSI/ADX via S2 computation)
                    # Get trend_strength from S2 scores (already computed in _s2_manage)
                    s2_temp = self._s2_manage(contract, chain, features)
                    trend_strength = float(s2_temp.get("scores", {}).get("trend_strength", 0.0))
                    momentum_positive = trend_strength >= 0.6  # Threshold: 0.6 (tunable)
                    
                    # All conditions must be met for S2 → S3
                    if price_above_ema333 and ema_slopes_up and momentum_positive:
                        # Compute S3 scores
                        s3 = self._compute_s3_scores(contract, chain, features)
                        if s3:
                            # S3 uses "flags" block (not "flag") per spec
                            payload = self._build_payload("S3", features, {
                                "scores": s3.get("scores", {}),
                                "diagnostics": s3.get("diagnostics", {}),
                            })
                            # Add flags block separately for S3
                            payload["flags"] = s3.get("flags", {})
                            # Add sr_context: asset-wide halo and ordered S/R list from S1
                            try:
                                ta_local = self._read_ta(features)
                                atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                                last_px = self._latest_close_1h(contract, chain).get("close") or 0.0
                                halo = max(0.5 * atr_1h, 0.03 * float(last_px)) if float(last_px) > 0 else 0.0
                            except Exception:
                                halo = 0.0
                            meta_ro = dict(features.get("uptrend_engine_meta") or {})
                            s1_ro = dict(meta_ro.get("s1") or {})
                            base_sr_level = float(s1_ro.get("base_sr_level") or 0.0)
                            flipped_sr_levels = list(s1_ro.get("flipped_sr_levels") or [])
                            # Ensure flipped list is price-desc ordered
                            try:
                                flipped_sr_levels.sort(key=lambda x: float(x.get("level") or 0.0), reverse=True)
                            except Exception:
                                pass
                            payload["sr_context"] = {
                                "halo": halo,
                                "base_sr_level": base_sr_level,
                                "flipped_sr_levels": flipped_sr_levels,
                            }
                            # Update features/meta from s3 (edx smoothing)
                            features = s3.get("features", features)
                
                # S2 management: For staying in S2 (S2→S2)
                # Note: S1→S2 is handled above, this handles staying in S2
                # We create S2 payload even if active=False (price not at S/R yet), as long as we have S1 meta
                # S3 is operating regime - if S3 conditions fail, we go to S0 (trend end), not back to S2
                if payload is None and prev_state == "S2":
                    meta_ro = dict(features.get("uptrend_engine_meta") or {})
                    s1_ro = dict(meta_ro.get("s1") or {})
                    if s1_ro:  # Only if we have S1 meta (legitimately in S2 state)
                        s2 = self._s2_manage(contract, chain, features)
                        base_sr_level = s1_ro.get("base_sr_level", 0.0)
                        flipped_sr_levels = s1_ro.get("flipped_sr_levels", [])
                        payload = self._build_payload("S2", features, {
                            "flag": {"uptrend_holding": s2.get("flags", {}).get("uptrend_holding", False)},
                            "scores": s2.get("scores", {}),  # Still computes TI/TS even if active=False
                            "base_sr_level": base_sr_level,
                            "flipped_sr_levels": flipped_sr_levels,
                        })
                        payload.setdefault("supports", {})
                        payload["supports"].update({
                            "current_sr_level": s2.get("current_sr", 0.0),  # May be 0 if not active yet
                            "halo": s2.get("halo", 0.0),
                        })
                        # Update meta persisted earlier
                        features = s2.get("features", features)
                
                # S2 fakeout check: ONLY in S2 (not in S1 - too early for fakeout)
                # NOTE: Only check fakeout if we're staying in S2 (not transitioning to S3)
                if prev_state == "S2" and payload is not None and payload.get("state") == "S2":
                    # Check if fakeout happened (price breaks below last_support_below_breakout)
                    meta_ro = dict(features.get("uptrend_engine_meta") or {})
                    if meta_ro.get("s1") and self._check_s1_fakeout(contract, chain, features):
                        # Invalidate cycle: clear S1/S2, emit event, fall back to S0
                        try:
                            meta_ro.pop("s1", None)
                            meta_ro.pop("s2", None)
                            features["uptrend_engine_meta"] = meta_ro
                        except Exception:
                            pass
                        payload = self._build_payload("S0", features, {"flag": {"watch_only": True}, "diagnostics": {"s2_fakeout": True}})
                        self._emit_event("s2_fakeout", {"token_contract": contract, "chain": chain, "ts": now.isoformat(), "payload": payload})
                
                # S3 → S0 transition: Emergency exit or persistent downtrend (8+ of 10 bars < EMA333)
                # This triggers trend reset: clear S1/S2 meta, transition to S0 with emergency_exit flag
                if payload is None and prev_state == "S3":
                    ema = ta.get("ema", {})
                    ema333 = float(ema.get("ema333_1h", 0.0))
                    if ema333 > 0:
                        try:
                            recent_rows = self._fetch_recent_ohlc(contract, chain, limit=10)
                            if len(recent_rows) >= 10:
                                below_count = 0
                                for r in recent_rows[-10:]:  # Last 10 bars
                                    px = float(r.get("close_native", 0.0))
                                    if px < ema333:
                                        below_count += 1
                                
                                # If 8+ out of 10 bars have price < EMA333 → persistent downtrend → transition S3 → S0
                                if below_count >= 8:
                                    # Compute S0 payload (trend reset)
                                    s0_comp = self._compute_s0_compression_and_baselines(contract, chain, ta, features)
                                    last = self._latest_close_1h(contract, chain)
                                    px = last["close"]
                                    low_now = last["low"]
                                    atr_1h = float((ta.get("atr") or {}).get("atr_1h") or 0.0)
                                    halo = max(0.5 * atr_1h, 0.03 * px) if px > 0 else 0.0
                                    
                                    # Build S0 payload with emergency_exit flag (for PM)
                                    payload = self._build_payload("S0", features, {
                                        "flag": {
                                            "watch_only": True,
                                            "emergency_exit": {
                                                "active": True,
                                                "reason": "persistent_downtrend",
                                                "ts": _now_iso(),
                                                "break_time": _now_iso(),
                                                "break_low": low_now or px,
                                                "ema333_at_break": ema333,
                                                "halo": halo,
                                                "bounce_zone": {
                                                    "low": ema333 - halo,
                                                    "high": ema333 + halo,
                                                },
                                                "below_count": below_count,
                                            }
                                        },
                                        "scores": {
                                            "compression_index": s0_comp.get("compression_index", 0.0),
                                            "atr_norm_slope": s0_comp.get("atr_norm_slope", 0.0),
                                            "dsep_fast": s0_comp.get("dsep_fast", 0.0),
                                            "dsep_mid": s0_comp.get("dsep_mid", 0.0),
                                        },
                                        "baselines": s0_comp.get("baselines", {}),
                                        "diagnostics": {"s3_exit": True, "reason": "persistent_downtrend", "below_count": below_count},
                                    })
                                    
                                    # Clear S1/S2 meta (reset cycle) - keep S0 baselines for future S1 breakout
                                    meta = dict(features.get("uptrend_engine_meta") or {})
                                    meta.pop("s1", None)
                                    meta.pop("s2", None)
                                    features["uptrend_engine_meta"] = meta
                                    
                                    # Emit transition event
                                    self._emit_event("s3_exit", {"token_contract": contract, "chain": chain, "ts": now.isoformat(), "payload": payload})
                        except Exception:
                            pass  # If check fails, continue to S3 regime
                
                # S0 explicit stay: If in S0 and no S1 breakout, explicitly stay in S0 (don't fall through to S3)
                if payload is None and prev_state == "S0":
                    s0_comp = self._compute_s0_compression_and_baselines(contract, chain, ta, features)
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "scores": {
                            "compression_index": s0_comp.get("compression_index", 0.0),
                            "atr_norm_slope": s0_comp.get("atr_norm_slope", 0.0),
                            "dsep_fast": s0_comp.get("dsep_fast", 0.0),
                            "dsep_mid": s0_comp.get("dsep_mid", 0.0),
                        },
                        "baselines": s0_comp.get("baselines", {}),
                    })
                    # Update features from S0 computation
                    features = dict(features)  # Ensure we have updated meta
                
                # NOTE: S2 → S3 transition is handled earlier (line 1279) before S2 stay check
                # S3 explicit stay: If in S3 and not transitioning to S0, stay in S3
                if payload is None and prev_state == "S3":
                    s3 = self._compute_s3_scores(contract, chain, features)
                    if s3:
                        # S3 uses "flags" block (not "flag") per spec
                        payload = self._build_payload("S3", features, {
                            "scores": s3.get("scores", {}),
                            "diagnostics": s3.get("diagnostics", {}),
                        })
                        # Add flags block separately for S3
                        payload["flags"] = s3.get("flags", {})
                        # Add sr_context: asset-wide halo and ordered S/R list from S1
                        try:
                            ta_local = self._read_ta(features)
                            atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                            last_px = self._latest_close_1h(contract, chain).get("close") or 0.0
                            halo = max(0.5 * atr_1h, 0.03 * float(last_px)) if float(last_px) > 0 else 0.0
                        except Exception:
                            halo = 0.0
                        meta_ro = dict(features.get("uptrend_engine_meta") or {})
                        s1_ro = dict(meta_ro.get("s1") or {})
                        base_sr_level = float(s1_ro.get("base_sr_level") or 0.0)
                        flipped_sr_levels = list(s1_ro.get("flipped_sr_levels") or [])
                        # Ensure flipped list is price-desc ordered
                        try:
                            flipped_sr_levels.sort(key=lambda x: float(x.get("level") or 0.0), reverse=True)
                        except Exception:
                            pass
                        payload["sr_context"] = {
                            "halo": halo,
                            "base_sr_level": base_sr_level,
                            "flipped_sr_levels": flipped_sr_levels,
                        }
                        # Update features/meta from s3 (edx smoothing)
                        features = s3.get("features", features)
                
                # Default S0 fallback: if somehow nothing matched, default to S0
                if payload is None:
                    s0_comp = self._compute_s0_compression_and_baselines(contract, chain, ta, features)
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "scores": {
                            "compression_index": s0_comp.get("compression_index", 0.0),
                            "atr_norm_slope": s0_comp.get("atr_norm_slope", 0.0),
                            "dsep_fast": s0_comp.get("dsep_fast", 0.0),
                            "dsep_mid": s0_comp.get("dsep_mid", 0.0),
                        },
                        "baselines": s0_comp.get("baselines", {}),
                    })
                    features = dict(features)

                # Get current state for emergency exit flag placement
                curr_state = str(payload.get("state") or "")
                
                # Emergency exit (EMA333 kill-switch flag) with bounce window tracking
                # NOTE: This flag is only set in S3 (not in S0). S3 → S0 transition handles the reset.
                prev_em_active = bool((prev_payload.get("flag") or prev_payload.get("flags") or {}).get("emergency_exit", {}).get("active") or False)
                
                # Only set emergency exit flag if we're in S3 (not in S0)
                if curr_state == "S3":
                    try:
                        ta_local = self._read_ta(features)
                        ema333 = float((ta_local.get("ema") or {}).get("ema333_1h") or 0.0)
                        last = self._latest_close_1h(contract, chain)
                        px = last["close"]
                        low_now = last["low"]
                        atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                        
                        # Immediate flag: Set flag when price < EMA333 (even if not yet persistent)
                        # Transition to S0 happens above if persistent (8+ of 10 bars)
                        if ema333 > 0.0 and px < ema333:
                            # Check if we're already tracking a bounce window
                            meta_em = dict(features.get("uptrend_engine_meta") or {})
                            em_meta = dict(meta_em.get("emergency_exit") or {})
                            break_ts_iso = str(em_meta.get("break_time") or _now_iso())
                            
                            # Parse break time and compute window expiry
                            try:
                                from datetime import datetime as dt
                                break_dt = dt.fromisoformat(break_ts_iso.replace('Z', '+00:00'))
                                window_expiry = break_dt.replace(tzinfo=timezone.utc).timestamp() + (Constants.BOUNCE_WINDOW_BARS * 3600)
                                now_ts = now.timestamp()
                                window_active = now_ts < window_expiry
                            except Exception:
                                break_dt = now
                                window_expiry = now.timestamp() + (Constants.BOUNCE_WINDOW_BARS * 3600)
                                window_active = True
                            
                            # Set flag block (S3 uses "flags", others use "flag")
                            if curr_state == "S3":
                                flags_block = payload.setdefault("flags", {})
                            else:
                                flags_block = payload.setdefault("flag", {})
                            
                            em = flags_block.setdefault("emergency_exit", {})
                            halo = max(0.5 * atr_1h, 0.03 * px) if px > 0 else 0.0
                            
                            # If this is a new activation, set break time
                            if not prev_em_active:
                                em_meta["break_time"] = _now_iso()
                                em_meta["break_low"] = low_now or px
                                em_meta["ema333_at_break"] = ema333
                                meta_em["emergency_exit"] = em_meta
                                features["uptrend_engine_meta"] = meta_em
                            
                            break_time_iso = str(em_meta.get("break_time") or _now_iso())
                            break_low = float(em_meta.get("break_low") or px)
                            ema333_at_break = float(em_meta.get("ema333_at_break") or ema333)
                            
                            em.update({
                                "active": True,
                                "reason": "close_below_ema333",
                                "ts": _now_iso(),
                                "break_time": break_time_iso,
                                "break_low": break_low,
                                "ema333_at_break": ema333_at_break,
                                "halo": halo,
                                "bounce_zone": {
                                    "low": ema333 - halo,
                                    "high": ema333 + halo,
                                },
                                "window_active": window_active,
                                "window_expires_at": datetime.fromtimestamp(window_expiry, tz=timezone.utc).isoformat() if window_active else None,
                            })
                            
                            # Suggested action
                            if atr_1h > 0 and low_now < (break_low - 0.5 * atr_1h):
                                em["suggested_action"] = "exit_immediately_new_low"
                            elif window_active:
                                bounced = (px - break_low) >= (0.5 * atr_1h) if atr_1h > 0 else False
                                in_zone = (ema333 - halo) <= px <= (ema333 + halo)
                                if in_zone and bounced:
                                    em["suggested_action"] = "exit_on_bounce_zone_touch"
                                else:
                                    em["suggested_action"] = "monitor"
                            else:
                                em["suggested_action"] = "window_expired_exit"
                            
                            # Track state change for event emission
                            if not prev_em_active:
                                payload["_emergency_exit_just_activated"] = True
                        else:
                            # Price recovered above EMA333 - check if we need to emit off event
                            if prev_em_active:
                                payload["_emergency_exit_just_deactivated"] = True
                                # Clear bounce window meta
                                meta_em = dict(features.get("uptrend_engine_meta") or {})
                                meta_em.pop("emergency_exit", None)
                                features["uptrend_engine_meta"] = meta_em
                    except Exception:
                        pass

                new_features = dict(features)
                new_features["uptrend_engine"] = payload
                self._write_features(pid, new_features)
                updated += 1

                # Scores log policy: base scores every tick; full diagnostics only on events
                base_scores = payload.get("scores") or {}
                should_log_full = False
                
                # Determine if this is an event (state transition or threshold crossing)
                is_state_transition = (curr_state != prev_state)
                em_just_activated = payload.pop("_emergency_exit_just_activated", None)
                em_just_deactivated = payload.pop("_emergency_exit_just_deactivated", None)
                is_emergency_exit_change = bool(em_just_activated or em_just_deactivated)
                
                if is_state_transition or is_emergency_exit_change:
                    should_log_full = True
                
                # Always append base scores (cheap, essential)
                self._append_scores_log(contract, chain, curr_state, base_scores)
                
                # Append full diagnostics only on events
                if should_log_full:
                    full_diag = payload.get("diagnostics") or {}
                    if full_diag:
                        try:
                            self.sb.table("uptrend_scores_log").insert({
                                "token_contract": contract,
                                "chain": chain,
                                "ts": _now_iso(),
                                "state": curr_state,
                                "scores": base_scores,
                                "diagnostics": full_diag,
                                "event_type": "state_transition" if is_state_transition else ("emergency_exit_change" if is_emergency_exit_change else "threshold_crossing"),
                            }).execute()
                        except Exception:
                            pass

                # Emit events on transitions and emergency exit changes
                event_payload = {"token_contract": contract, "chain": chain, "ts": now.isoformat(), "payload": payload}
                if curr_state == "S1" and prev_state != "S1":
                    self._emit_event("s1_breakout", event_payload)
                if curr_state == "S2" and prev_state != "S2":
                    self._emit_event("s2_support_touch", event_payload)
                if curr_state == "S3" and prev_state != "S3":
                    self._emit_event("s3_active", event_payload)
                
                # Emergency exit events
                if em_just_activated:
                    self._emit_event("emergency_exit_on", event_payload)
                if em_just_deactivated:
                    self._emit_event("emergency_exit_off", event_payload)
            except Exception as e:
                logger.debug("uptrend_engine_v2 skipped position: %s", e)
        logger.info("Uptrend engine v2 updated %d positions", updated)
        return updated


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    UptrendEngineV2().run()


if __name__ == "__main__":
    main()


