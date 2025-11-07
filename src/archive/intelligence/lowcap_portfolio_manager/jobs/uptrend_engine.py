from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client  # type: ignore

from src.intelligence.lowcap_portfolio_manager.events import bus
from src.intelligence.lowcap_portfolio_manager.utils.zigzag import detect_swings


logger = logging.getLogger(__name__)


class UptrendEngine:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)

    def _active_positions(self) -> List[Dict[str, Any]]:
        res = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,features")
            .eq("status", "active")
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _emit_event(self, event: str, payload: dict) -> None:
        try:
            bus.emit(event, payload)
        except Exception:
            pass
        # Persist to events table (best-effort)
        try:
            contract = str(payload.get("token_contract") or "")
            chain = str(payload.get("chain") or "")
            ts = str(payload.get("ts") or datetime.now(timezone.utc).isoformat())
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

    def _geometry_diagonals(self, features: Dict[str, Any]) -> Dict[str, float]:
        geom = features.get("geometry") or {}
        levels = geom.get("diag_levels") or {}
        
        # Get both diagonals from geometry system
        lower_diag = 0.0
        upper_diag = 0.0
        
        try:
            supp = levels.get("diag_support") or {}
            lower_diag = float(supp.get("price") or 0.0)
        except Exception:
            pass
            
        try:
            res = levels.get("diag_resistance") or {}
            upper_diag = float(res.get("price") or 0.0)
        except Exception:
            pass
        
        # Fallbacks to legacy structure
        if lower_diag == 0.0:
            maybe_levels = features.get("levels") or {}
            try:
                lower_diag = float(maybe_levels.get("lower_diagonal") or 0.0)
            except Exception:
                pass
        
        return {
            "lower_diagonal": lower_diag,
            "upper_diagonal": upper_diag
        }

    def _geometry_lower_diagonal(self, features: Dict[str, Any]) -> float:
        """Legacy method - use _geometry_diagonals for new code"""
        diagonals = self._geometry_diagonals(features)
        return diagonals["lower_diagonal"]

    def _s2_supports(self, contract: str, chain: str, features: Dict[str, Any], closes: List[float], highs: List[float], lows: List[float], ema50_last: float, atr_last: float, px_last: float) -> Dict[str, Any]:
        # Determine available supports
        avwap_anchor_ts = self._get_avwap_anchor_ts(features)
        avwap_val = self._compute_avwap_current(contract, chain, avwap_anchor_ts) if avwap_anchor_ts else 0.0
        diagonal_val = self._geometry_lower_diagonal(features)
        supports_order = ["AVWAP", "EMA50", "diagonal"]
        support_levels = {
            "AVWAP": float(avwap_val or 0.0),
            "EMA50": float(ema50_last or 0.0),
            "diagonal": float(diagonal_val or 0.0),
        }
        # Choose highest tier available for touch check
        halo = max(0.5 * atr_last, 0.03 * px_last) if px_last > 0 else 0.0
        meta = features.get("uptrend_engine_meta") or {}
        s2_meta = dict(meta.get("s2") or {})
        current_support = s2_meta.get("current_support")
        t0_ts = s2_meta.get("t0_ts")
        # Determine close and low of latest bar
        low_last = lows[-1] if lows else px_last

        # First touch logic: pick top-most available support that has non-zero level
        def first_available_support() -> Optional[str]:
            for name in supports_order:
                if support_levels.get(name, 0.0) > 0:
                    return name
            return None

        # Initialize on first valid touch if not set
        if not current_support:
            cand = first_available_support()
            if cand:
                s_level = support_levels[cand]
                # Touch halo + close ≥ support
                if low_last <= s_level + halo and px_last >= s_level:
                    current_support = cand
                    t0_ts = self._latest_close_1h(contract, chain).get("ts")
                    s2_meta = {"current_support": current_support, "t0_ts": t0_ts, "touch_confirm": True}
        else:
            # Step down if close < current support level
            s_level = support_levels.get(current_support, 0.0)
            if s_level > 0 and px_last < s_level:
                # Move to next lower
                if current_support == "AVWAP":
                    next_s = "EMA50" if support_levels.get("EMA50", 0.0) > 0 else "diagonal"
                elif current_support == "EMA50":
                    next_s = "diagonal"
                else:
                    next_s = None
                if next_s:
                    current_support = next_s
                    # keep same t0_ts (per spec)
                    s2_meta["current_support"] = current_support
                    s2_meta["dent_pending"] = True
            # Reclaim higher
            higher = None
            if current_support == "EMA50" and support_levels.get("AVWAP", 0.0) > 0 and px_last >= support_levels["AVWAP"]:
                higher = "AVWAP"
            if current_support == "diagonal":
                if support_levels.get("EMA50", 0.0) > 0 and px_last >= support_levels["EMA50"]:
                    higher = "EMA50"
                if support_levels.get("AVWAP", 0.0) > 0 and px_last >= support_levels["AVWAP"]:
                    higher = "AVWAP"
            if higher:
                current_support = higher
                s2_meta["current_support"] = current_support
                s2_meta["reclaim_boost_pending"] = True

        # Compute persistence components since t0 if available
        support_persistence = 0.0
        reaction_quality = 0.0
        close_persistence = 0.0
        absorption_wicks = 0.0
        touch_confirm = bool(s2_meta.get("touch_confirm"))
        if t0_ts and current_support:
            # Fetch bars since t0
            rows = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp, close_native, low_native, high_native")
                .eq("token_contract", contract)
                .eq("chain", chain)
                .eq("timeframe", "1h")
                .gte("timestamp", str(t0_ts))
                .order("timestamp", desc=False)
                .limit(200)
                .execute()
                .data
                or []
            )
            closes_s2 = [float(r.get("close_native") or 0.0) for r in rows]
            lows_s2 = [float(r.get("low_native") or 0.0) for r in rows]
            highs_s2 = [float(r.get("high_native") or 0.0) for r in rows]
            s_level_now = support_levels.get(current_support, 0.0)
            # close_persistence
            cnt_closes = sum(1 for v in closes_s2 if v >= s_level_now)
            import math
            close_persistence = 1.0 - math.exp(-(cnt_closes / 6.0))
            # absorption_wicks
            wick_cnt = sum(1 for lo, cl in zip(lows_s2, closes_s2) if lo < s_level_now and cl >= s_level_now)
            absorption_wicks = 1.0 - math.exp(-(wick_cnt / 2.0))
            # reaction_quality using max high since t0
            if highs_s2:
                bounce_atr = (max(highs_s2) - s_level_now) / max(atr_last, 1e-9)
                reaction_quality = min(1.0, bounce_atr / 1.0)
            # combine
            support_persistence = 0.25 * (1.0 if touch_confirm else 0.0) + 0.20 * reaction_quality + 0.40 * close_persistence + 0.15 * absorption_wicks

        return {
            "meta": s2_meta,
            "current_support": current_support,
            "order": supports_order,
            "levels": support_levels,
            "halo": halo,
            "scores": {
                "support_persistence": support_persistence,
                "reaction_quality": reaction_quality,
                "close_persistence": close_persistence,
                "absorption_wicks": absorption_wicks,
            },
        }

    def _update_emergency_exit(self, payload: Dict[str, Any], features: Dict[str, Any], contract: str, chain: str) -> Dict[str, Any]:
        ta = features.get("ta", {})
        ema50 = float(ta.get("ema", {}).get("ema50_1h") or 0.0)
        atr_1h = float(ta.get("atr", {}).get("atr_1h") or 0.0)
        last = self._latest_close_1h(contract, chain)
        px = last["close"]
        low_now = last["low"]
        diag = self._geometry_lower_diagonal(features)
        flag = payload.setdefault("flag", {})
        em = flag.setdefault("emergency_exit", {}) or {}
        active = bool(em.get("active"))
        now_iso = datetime.now(timezone.utc).isoformat()

        # Compute halo
        halo = max(0.5 * atr_1h, 0.03 * px) if px > 0 else 0.0

        # Activation: require both EMA50 and diagonal present and price below both
        if not active and ema50 > 0 and diag > 0 and px > 0 and (px < ema50 and px < diag):
            em = {
                "active": True,
                "break_time": now_iso,
                "break_low": low_now or px,
                "ema50_at_break": ema50,
                "diagonal_at_break": diag,
                "halo": halo,
                "bounce_zone": {
                    "low": min(ema50, diag) - halo,
                    "high": max(ema50, diag) + halo,
                },
                "t_expires": None,
            }
            flag["emergency_exit"] = em
            self._emit_event("emergency_exit_on", {"token_contract": contract, "chain": chain, "ts": now_iso, "payload": em})
            return payload

        # If active: manage cancel on reclaim of both; compute suggested actions
        if active:
            # cancel if reclaimed both
            if px >= ema50 and px >= diag:
                em = {"active": False}
                flag["emergency_exit"] = em
                self._emit_event("emergency_exit_off", {"token_contract": contract, "chain": chain, "ts": now_iso})
                return payload

            # Update halo and zone on the fly
            em["halo"] = halo
            em["bounce_zone"] = {
                "low": min(em.get("ema50_at_break", ema50), em.get("diagonal_at_break", diag)) - halo,
                "high": max(em.get("ema50_at_break", ema50), em.get("diagonal_at_break", diag)) + halo,
            }
            # Suggest action if new low extends far below break low
            try:
                br_low = float(em.get("break_low") or 0.0)
            except Exception:
                br_low = 0.0
            if low_now and br_low and atr_1h > 0 and (low_now < br_low - 0.5 * atr_1h):
                em["suggested_action"] = "exit_immediately_new_low"
            else:
                # If price enters bounce zone and bounced ≥ 0.5 ATR from break low, suggest exit on touch
                in_zone = em["bounce_zone"]["low"] <= px <= em["bounce_zone"]["high"]
                bounced = (px - (br_low or px)) >= 0.5 * atr_1h if atr_1h > 0 else False
                if in_zone and bounced:
                    em["suggested_action"] = "exit_on_bounce_zone_touch"
                else:
                    em["suggested_action"] = em.get("suggested_action", "monitor")
            flag["emergency_exit"] = em
        return payload

    def _unified_payload(self, state: str, features: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal stub – wire TA metrics into unified schema; scoring to be added next step
        now = datetime.now(timezone.utc).isoformat()
        ta = features.get("ta", {})
        ema = ta.get("ema", {})
        atr = ta.get("atr", {})
        adx = ta.get("adx", {})
        vol = ta.get("volume", {})
        
        # Get diagonal levels from geometry
        diagonals = self._geometry_diagonals(features)
        
        return {
            "state": state,
            "timeframe": "1h",
            "t0": now,
            "flag": {},
            "scores": {},
            "levels": {
                "ema20": float(ema.get("ema20_1h") or 0.0),
                "ema50": float(ema.get("ema50_1h") or 0.0),
                "lower_diagonal": diagonals["lower_diagonal"],
                "upper_diagonal": diagonals["upper_diagonal"],
            },
            "diagnostics": {
                "atr_1h": float(atr.get("atr_1h") or 0.0),
                "adx_1h": float(adx.get("adx_1h") or 0.0),
                "vo_z_1h": float(vol.get("vo_z_1h") or 0.0),
            },
            "meta": {"atr_period": 14, "vo_z_window": 64, "sigmoid_scale": {"rsi": 0.5, "adx": 0.3}},
        }

    # ----- Series helpers for scoring -----
    def _fetch_ohlc_1h_series(self, contract: str, chain: str, limit: int = 120) -> List[Dict[str, Any]]:
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

    def _ema_series(self, vals: List[float], span: int) -> List[float]:
        if not vals:
            return []
        alpha = 2.0 / (span + 1)
        out = [vals[0]]
        for v in vals[1:]:
            out.append(alpha * v + (1 - alpha) * out[-1])
        return out

    def _atr_series(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        if len(highs) < 2:
            return []
        trs: List[float] = []
        prev_c = closes[0]
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - prev_c), abs(prev_c - lows[i]))
            trs.append(tr)
            prev_c = closes[i]
        if not trs:
            return []
        atrs: List[float] = []
        # Wilder init
        atr = sum(trs[: period]) / max(1, min(period, len(trs)))
        atrs.extend([atr])
        for tr in trs[period:]:
            atr = (atr * (period - 1) + tr) / period
            atrs.append(atr)
        # align length to closes
        # trs length is len(closes)-1; atrs starts after warmup; pad with first value
        pad = len(closes) - 1 - len(atrs)
        if pad > 0:
            atrs = [atrs[0]] * pad + atrs
        atrs = [atrs[0]] + atrs  # align to same indices as closes
        return atrs

    def _rsi_series(self, closes: List[float], period: int = 14) -> List[float]:
        out: List[float] = []
        if len(closes) <= period:
            return [50.0] * len(closes)
        gains: List[float] = []
        losses: List[float] = []
        for i in range(1, len(closes)):
            ch = closes[i] - closes[i - 1]
            gains.append(max(0.0, ch))
            losses.append(max(0.0, -ch))
        # First avg
        avg_gain = sum(gains[: period]) / period
        avg_loss = sum(losses[: period]) / period or 1e-9
        rs = avg_gain / avg_loss
        out = [100.0 - (100.0 / (1.0 + rs))]
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period or 1e-9
            rs = avg_gain / avg_loss
            out.append(100.0 - (100.0 / (1.0 + rs)))
        # align
        pad = len(closes) - len(out)
        return [50.0] * pad + out

    def _lin_slope(self, vals: List[float], win: int) -> float:
        n = min(win, len(vals))
        if n < 3:
            return 0.0
        xs = list(range(n))
        ys = vals[-n:]
        xbar = sum(xs) / n
        ybar = sum(ys) / n
        num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
        den = sum((x - xbar) ** 2 for x in xs) or 1.0
        return num / den

    def _sigmoid(self, x: float, k: float) -> float:
        import math
        return 1.0 / (1.0 + math.exp(-x / max(k, 1e-9)))

    def _compute_euphoria(self, closes: List[float], ema20: List[float], atrs: List[float], avwap_last: Optional[float], vo_z_1h_series: List[float], upper_diagonal: Optional[float] = None) -> float:
        if not closes or not ema20 or not atrs:
            return 0.0
        
        # ATR expansion - THE core euphoria signal (increased weight)
        import statistics
        atr_expansion = 0.0
        if len(atrs) >= 20:
            avg20 = statistics.fmean(atrs[-20:]) or 1e-9
            atr_expansion = 0.40 * self._sigmoid((atrs[-1] / avg20) - 1.0, 1.0)  # Increased from 0.20
        
        # Distance from EMA20 rail (reduced weight)
        ema_dist = (closes[-1] - ema20[-1]) / max(atrs[-1], 1e-9)
        distance_term = 0.20 * self._sigmoid(ema_dist - 2.0, 1.0)  # Reduced from 0.30
        
        # AVWAP separation (reduced weight)
        avwap_term = 0.0
        if avwap_last and atrs[-1] > 0:
            avwap_dist = (closes[-1] - avwap_last) / atrs[-1]
            avwap_term = 0.15 * self._sigmoid(avwap_dist - 3.0, 1.0)  # Reduced from 0.20
        
        # Upper diagonal distance (new - big boost when above)
        upper_diag_term = 0.0
        if upper_diagonal and upper_diagonal > 0 and atrs[-1] > 0:
            upper_dist = (closes[-1] - upper_diagonal) / atrs[-1]
            # Big boost when above upper diagonal, smaller boost when approaching
            if upper_dist > 0:  # Above diagonal
                upper_diag_term = 0.20 * self._sigmoid(upper_dist / 1.0, 1.0)  # Big boost above
            else:  # Below diagonal
                upper_diag_term = 0.10 * self._sigmoid(-upper_dist / 2.0, 1.0)  # Smaller boost approaching
        
        # Volume burst (keep same)
        volume_term = 0.0
        if vo_z_1h_series:
            window = vo_z_1h_series[-12:] if len(vo_z_1h_series) >= 12 else vo_z_1h_series
            burst = sum(1 for z in window if z >= 2.0) / max(12.0, float(len(window)))
            volume_term = 0.05 * min(1.0, burst)  # Reduced from 0.10

        euphoria = atr_expansion + distance_term + avwap_term + upper_diag_term + volume_term
        return max(0.0, min(1.0, euphoria))

    def _compute_euphoria_series(self, closes: List[float], ema20: List[float], atrs: List[float], vo_z_1h_series: List[float], avwap_last: Optional[float], upper_diagonal: Optional[float] = None) -> List[float]:
        out: List[float] = []
        n = min(len(closes), len(ema20), len(atrs))
        for i in range(n):
            c = closes[: i + 1]
            e20 = ema20[: i + 1]
            a = atrs[: i + 1]
            vz = vo_z_1h_series[: i + 1] if vo_z_1h_series else []
            out.append(self._compute_euphoria(c, e20, a, avwap_last, vo_z_1h_series=vz, upper_diagonal=upper_diagonal))
        return out

    def _get_avwap_anchor_ts(self, features: Dict[str, Any]) -> Optional[str]:
        meta = features.get("uptrend_engine_meta") or {}
        ts = meta.get("avwap_flip_anchor_ts")
        return str(ts) if ts else None

    def _compute_avwap_current(self, contract: str, chain: str, anchor_ts: str) -> Optional[float]:
        # Compute VWAP since anchor using 1h close*volume / volume
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .gte("timestamp", anchor_ts)
            .order("timestamp", desc=False)
            .limit(500)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        num = 0.0
        den = 0.0
        for r in rows:
            px = float(r.get("close_native") or 0.0)
            v = float(r.get("volume") or 0.0)
            num += px * v
            den += v
        if den <= 0:
            return None
        return num / den

    def _compute_continuation_quality(self, closes: List[float], highs: List[float], lows: List[float], atrs: List[float], ema20: List[float], vo_z_series: List[float], upper_diagonal: Optional[float]) -> Dict[str, float]:
        # ZigZag legs
        swings = detect_swings(closes, atrs, highs=highs, lows=lows, lambda_mult=1.2, backstep=3, min_leg_bars=4)
        up = swings.get("up_legs") or []
        down = swings.get("down_legs") or []
        import statistics
        def mean_safe(arr: List[float]) -> float:
            return statistics.fmean(arr) if arr else 0.0
        up_amp = mean_safe([l["amplitude_atr"] for l in up])
        down_amp = mean_safe([l["amplitude_atr"] for l in down])
        up_time = mean_safe([l["duration_bars"] for l in up])
        down_time = mean_safe([l["duration_bars"] for l in down])
        power_score = self._sigmoid(((up_amp / max(down_amp, 1e-9)) - 1.0) / 0.3, 1.0)
        time_score = self._sigmoid(((down_time / max(up_time, 1e-9)) - 1.0) / 0.3, 1.0)
        continuation_quality_base = 0.6 * power_score + 0.4 * time_score

        # Pullback quality
        if closes and ema20 and atrs and atrs[-1] > 0:
            dist_ema = abs((closes[-1] - ema20[-1]) / atrs[-1])
            pull_loc = self._sigmoid((0.8 - dist_ema) / 0.3, 1.0)
        else:
            pull_loc = 0.5
        pullback_quality = pull_loc  # simplified fib proxy omitted

        # Absorption score over last 3 bars
        window = 3
        wick_down_sum = 0.0
        vz_sum = 0.0
        if lows and closes:
            for i in range(max(0, len(closes) - window), len(closes)):
                wick_down_sum += max(0.0, (closes[i] - lows[i]))
        if vo_z_series:
            for z in vo_z_series[-window:]:
                vz_sum += max(0.0, z)
        wick_down_atr = wick_down_sum / max(atrs[-1], 1e-9) if atrs else 0.0
        absorption_score = 0.6 * self._sigmoid((wick_down_atr - 0.3) / 0.2, 1.0) + 0.4 * self._sigmoid((vz_sum) / 3.0, 1.0)

        # Channel penalty near upper rail
        if upper_diagonal and atrs and atrs[-1] > 0:
            dist_upper = (upper_diagonal - closes[-1]) / atrs[-1]
            channel_penalty = self._sigmoid((( - dist_upper) - 0.5) / 0.3, 1.0) if dist_upper < 0 else 0.0
        else:
            channel_penalty = 0.0

        # Combine
        continuation_quality = 0.5 * continuation_quality_base + 0.5 * pullback_quality
        continuation_quality = max(continuation_quality, continuation_quality + 0.1 * absorption_score)
        continuation_quality *= (1 - 0.25 * channel_penalty)
        continuation_quality = min(1.0, max(0.0, continuation_quality))

        # Rough channel position diagnostic
        channel_position = "mid"
        if upper_diagonal and atrs and atrs[-1] > 0:
            if abs((upper_diagonal - closes[-1]) / atrs[-1]) <= 0.75:
                channel_position = "upper"
        # lower_diagonal optional from geometry for completeness (not strictly needed here)

        return {
            "continuation_quality": continuation_quality,
            "absorption_score": absorption_score,
            "channel_penalty": channel_penalty,
            "power_score": power_score,
            "time_score": time_score,
            "channel_position": channel_position,
        }

    def _score_and_state(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._fetch_ohlc_1h_series(contract, chain, limit=120)
        if len(rows) < 30:
            # Fallback to simple state
            ta = features.get("ta", {})
            ema = ta.get("ema", {})
            state = "S2" if float(ema.get("ema20_1h") or 0.0) > float(ema.get("ema50_1h") or 0.0) else "S0"
            return {"state": state, "scores": {}, "flags": {}, "levels": {}}

        closes = [float(r.get("close_native") or 0.0) for r in rows]
        highs = [float(r.get("high_native") or 0.0) for r in rows]
        lows = [float(r.get("low_native") or 0.0) for r in rows]
        vols = [float(r.get("volume") or 0.0) for r in rows]

        ema20 = self._ema_series(closes, 20)
        ema50 = self._ema_series(closes, 50)
        atrs = self._atr_series(highs, lows, closes, 14)
        rsi = self._rsi_series(closes, 14)
        # ADX approx using ATR as proxy strength slope (placeholder until full ADX series implemented)
        adx_series = self._ema_series([abs(self._lin_slope(closes[max(0,i-14):i+1], min(10, i+1))) * 100 for i in range(len(closes))], 5)
        adx_now = adx_series[-1] if adx_series else 0.0

        # Volume z for 1h – reuse last known or compute simple z if absent
        ta_vol = float((features.get("ta", {}).get("volume", {}) or {}).get("vo_z_1h") or 0.0)
        vo_series = [ta_vol] * len(closes)

        # AVWAP last for euphoria term if anchor exists
        avwap_anchor_ts = self._get_avwap_anchor_ts(features)
        avwap_last = self._compute_avwap_current(contract, chain, avwap_anchor_ts) if avwap_anchor_ts else None
        
        # Get upper diagonal for euphoria calculation
        diagonals = self._geometry_diagonals(features)
        upper_diagonal = diagonals["upper_diagonal"] if diagonals["upper_diagonal"] > 0 else None
        
        euphoria_series = self._compute_euphoria_series(closes, ema20, atrs, vo_series, avwap_last, upper_diagonal)
        # ADX floor cap for euphoria: if ADX < 18, cap euphoria at 0.65 (applied per-bar)
        if euphoria_series and adx_series:
            euphoria_series = [
                (min(v, 0.65) if (adx_series[i] < 18.0) else v)
                for i, v in enumerate(euphoria_series)
            ]
        euphoria = euphoria_series[-1] if euphoria_series else 0.0
        cont_block = self._compute_continuation_quality(closes, highs, lows, atrs, ema20, vo_series, upper_diagonal)
        continuation = cont_block["continuation_quality"]

        ema20_gt_50 = (ema20[-1] > ema50[-1])
        trend_healthy = 1.0 if (ema20_gt_50 and self._lin_slope(ema20, 5) > 0 and self._lin_slope(ema50, 5) > 0) else 0.0
        trend_strength = max(0.0, min(1.0, 0.6 * self._sigmoid(self._lin_slope(rsi, 10) / 0.5, 1.0) + 0.4 * self._sigmoid(self._lin_slope(adx_series, 10) / 0.3, 1.0)))
        # ADX floor guard: cap trend_strength when ADX is weak to avoid momentum mirages
        if adx_now < 16.0:
            trend_strength = min(trend_strength, 0.55)

        # Hysteresis implementation for flags
        meta = features.get("uptrend_engine_meta") or {}
        hysteresis = meta.get("hysteresis", {})
        
        # Initialize hysteresis counters if not present
        if "can_still_enter" not in hysteresis:
            hysteresis["can_still_enter"] = {"on_count": 0, "off_count": 0, "current_state": False}
        if "trend_healthy" not in hysteresis:
            hysteresis["trend_healthy"] = {"on_count": 0, "off_count": 0, "current_state": False}
        if "euphoria_building" not in hysteresis:
            hysteresis["euphoria_building"] = {"on_count": 0, "off_count": 0, "current_state": False}
        
        # Apply hysteresis logic
        def apply_hysteresis(flag_name: str, current_value: float, on_threshold: float, off_threshold: float) -> bool:
            state = hysteresis[flag_name]
            
            if current_value >= on_threshold:
                state["on_count"] += 1
                state["off_count"] = 0
                if state["on_count"] >= 3:
                    state["current_state"] = True
            elif current_value < off_threshold:
                state["off_count"] += 1
                state["on_count"] = 0
                if state["off_count"] >= 3:
                    state["current_state"] = False
            
            return state["current_state"]
        
        # Apply hysteresis to each flag
        flags: Dict[str, Any] = {}
        flags["euphoria_building"] = apply_hysteresis("euphoria_building", euphoria, 0.70, 0.55)
        flags["can_still_enter"] = apply_hysteresis("can_still_enter", continuation, 0.70, 0.60)
        flags["trend_healthy"] = apply_hysteresis("trend_healthy", trend_healthy, 0.70, 0.60)

        # S1 detection: diagonal break + EMA flip + 1h VO_z cluster
        geom = features.get("geometry") or {}
        diag_break = str(geom.get("diag_break") or "none").lower()
        vo_cluster = bool((features.get("ta", {}).get("volume", {}) or {}).get("vo_z_cluster_1h") or False)
        ema_flip_now = ema20[-1] > ema50[-1] and ema20[-2] <= ema50[-2]

        if flags["euphoria_building"]:
            state = "S4"
        elif diag_break == "bull" and ema_flip_now and vo_cluster:
            state = "S1"
        elif ema20_gt_50:
            state = "S3" if flags["can_still_enter"] else "S2"
        else:
            state = "S0"

        # --- S2 support persistence and tier boosts ---
        s2 = self._s2_supports(contract, chain, features, closes, highs, lows, ema50[-1], atrs[-1], closes[-1])
        s2_scores = s2["scores"]
        # ema_alignment
        sep = ((ema20[-1] - ema50[-1]) / max(ema50[-1], 1e-9)) * 100.0
        ema_alignment = (1.0 if ema20[-1] > ema50[-1] else 0.0) * 0.33
        ema_alignment += (1.0 if self._lin_slope(ema20, 5) > 0 and self._lin_slope(ema50, 5) > 0 else 0.0) * 0.33
        ema_alignment += 0.33 * self._sigmoid(sep, 10.0)
        # volatility_coherence
        s1_atr = float((features.get("uptrend_engine_meta") or {}).get("s1_atr") or 0.0)
        if s1_atr > 0.0:
            red = (atrs[-1] - s1_atr) / s1_atr
            volatility_coherence = self._sigmoid(-red / 0.3, 1.0)
        else:
            volatility_coherence = 0.5
        trend_integrity = 0.65 * s2_scores["support_persistence"] + 0.25 * ema_alignment + 0.10 * volatility_coherence
        # Apply tier boosts
        tier = s2.get("current_support") or "AVWAP"
        if tier == "EMA50":
            trend_integrity = min(1.0, trend_integrity * 1.15)
            trend_strength = min(1.0, trend_strength * 1.15)
        elif tier == "diagonal":
            trend_integrity = min(1.0, trend_integrity * 1.30)
            trend_strength = min(1.0, trend_strength * 1.30)
        # Apply dents/reclaim boosts if pending
        if s2["meta"].get("dent_pending"):
            trend_integrity *= 0.4
            trend_strength *= 0.6
            s2["meta"].pop("dent_pending", None)
        if s2["meta"].get("reclaim_boost_pending"):
            trend_integrity = min(1.0, trend_integrity * 1.3)
            trend_strength = min(1.0, trend_strength * 1.6)
            s2["meta"].pop("reclaim_boost_pending", None)

        # Update flags based on S2
        flags["uptrend_holding"] = bool(s2.get("current_support")) and (px_last := closes[-1]) >= max(0.0, s2["levels"].get(s2.get("current_support"), 0.0))
        
        # Enhanced uptrend_confirmed logic (from SM_UPTREND.MD)
        def check_monotonic_trend_strength(trend_strength_series: List[float], window: int = 5) -> bool:
            """Check if trend_strength is rising monotonically over last window bars"""
            if len(trend_strength_series) < window:
                return False
            recent_values = trend_strength_series[-window:]
            # Check if each value is >= previous (monotonic rising)
            for i in range(1, len(recent_values)):
                if recent_values[i] < recent_values[i-1]:
                    return False
            return True
        
        def compute_sr_reclaim_score(contract: str, chain: str, t0_ts: str) -> float:
            """Compute cumulative S/R reclaim score since t0"""
            if not t0_ts:
                return 0.0
            
            # Query S/R levels reclaimed since t0
            try:
                rows = (
                    self.sb.table("lowcap_sr_levels")
                    .select("level_score, reclaimed_at")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .gte("reclaimed_at", t0_ts)
                    .eq("status", "reclaimed")
                    .execute()
                    .data
                    or []
                )
                return sum(float(r.get("level_score", 0.0)) for r in rows)
            except Exception:
                return 0.0
        
        # Check all uptrend_confirmed conditions
        t0_ts = s2.get("meta", {}).get("t0_ts")
        sr_reclaim_score = compute_sr_reclaim_score(contract, chain, t0_ts) if t0_ts else 0.0
        
        # Create trend_strength series for monotonic check
        def compute_trend_strength_series(closes: List[float], rsi: List[float], adx_series: List[float], window: int = 6) -> List[float]:
            """Compute trend_strength for last window bars"""
            series = []
            min_len = min(len(closes), len(rsi), len(adx_series))
            start_idx = max(0, min_len - window)
            
            for i in range(start_idx, min_len):
                rsi_slope = self._lin_slope(rsi[:i+1], min(10, i+1))
                adx_slope = self._lin_slope(adx_series[:i+1], min(10, i+1))
                ts = max(0.0, min(1.0, 0.6 * self._sigmoid(rsi_slope / 0.5, 1.0) + 0.4 * self._sigmoid(adx_slope / 0.3, 1.0)))
                series.append(ts)
            
            return series
        
        trend_strength_series = compute_trend_strength_series(closes, rsi, adx_series, 6)
        
        flags["uptrend_confirmed"] = (
            s2_scores["support_persistence"] >= 0.6 and
            s2_scores["reaction_quality"] >= 0.3 and
            check_monotonic_trend_strength(trend_strength_series, 5) and
            sr_reclaim_score >= 30.0
        )

        # --- S5 cooldown & re-entry ---
        # Conditions: after S4, euphoria dropped (<0.55 for 2 bars) and two scores ≥ 0.6
        def s5_scores() -> Dict[str, float]:
            # structural_hold
            last_n = 10
            above_ema50 = 0
            above_diag = 0
            diag = self._geometry_lower_diagonal(features)
            for i in range(max(0, len(closes) - last_n), len(closes)):
                if closes[i] >= ema50[i]:
                    above_ema50 += 1
                if diag > 0 and closes[i] >= diag:
                    above_diag += 1
            above_ema50_ratio = above_ema50 / float(min(last_n, len(closes)) or 1)
            above_diagonal_ratio = above_diag / float(min(last_n, len(closes)) or 1)
            structural_hold = 0.6 * above_ema50_ratio + 0.4 * above_diagonal_ratio
            # volatility_cool using local 10-bar peak as proxy for S4 peak
            import statistics
            win = atrs[-10:] if len(atrs) >= 10 else atrs
            atr_peak = max(win) if win else (atrs[-1] if atrs else 0.0)
            ratio = (atrs[-1] / atr_peak) if atr_peak else 0.0
            if ratio > 1.2:
                volatility_cool = 0.3
            elif 0.6 <= ratio <= 1.0:
                volatility_cool = 1.0
            else:
                volatility_cool = 0.5
            # momentum_reset around RSI/ADX mids
            rsi_mid = 1.0 - abs((rsi[-1] if rsi else 50.0) - 50.0) / 50.0
            adx_now = adx_series[-1] if adx_series else 0.0
            adx_mid = self._sigmoid((25.0 - abs(adx_now - 25.0)) / 5.0, 1.0)
            momentum_reset = 0.6 * rsi_mid + 0.4 * adx_mid
            cooldown_integrity = 0.40 * structural_hold + 0.35 * volatility_cool + 0.25 * momentum_reset

            # reentry_readiness
            dist = (closes[-1] - ema50[-1]) / max(atrs[-1], 1e-9)
            location_quality = self._sigmoid(-abs(dist) / 0.5, 1.0)
            # compression quality via ATR slope 10
            atr_slope = self._lin_slope(atrs, 10)
            compression_quality = self._sigmoid(atr_slope / 0.2, 1.0)
            # early pulse via RSI/ADX slopes
            rsi_slope = self._lin_slope(rsi, 8)
            adx_slope = self._lin_slope(adx_series, 8)
            early_pulse = 0.5 * self._sigmoid(rsi_slope / 0.4, 1.0) + 0.5 * self._sigmoid(adx_slope / 0.3, 1.0)
            reentry_readiness = 0.45 * location_quality + 0.35 * compression_quality + 0.20 * early_pulse
            return {"cooldown_integrity": cooldown_integrity, "reentry_readiness": reentry_readiness}

        # S5 activation with hysteresis (2 consecutive bars above thresholds)
        s5 = s5_scores()
        euphoria_cool_passed = sum(1 for v in euphoria_series[-2:] if v < 0.55) >= 2 if len(euphoria_series) >= 2 else False
        
        # Initialize S5 hysteresis if not present
        if "s5_activation" not in hysteresis:
            hysteresis["s5_activation"] = {"on_count": 0, "off_count": 0, "current_state": False}
        
        s5_hyst = hysteresis["s5_activation"]
        cooldown_ok = s5["cooldown_integrity"] >= 0.6
        reentry_ok = s5["reentry_readiness"] >= 0.6
        both_ok = cooldown_ok and reentry_ok
        
        # Apply S5 hysteresis logic
        if both_ok:
            s5_hyst["on_count"] += 1
            s5_hyst["off_count"] = 0
            if s5_hyst["on_count"] >= 2:  # 2 consecutive bars
                s5_hyst["current_state"] = True
        elif not cooldown_ok or not reentry_ok:
            s5_hyst["off_count"] += 1
            s5_hyst["on_count"] = 0
            if s5_hyst["off_count"] >= 2:  # 2 consecutive bars below threshold
                s5_hyst["current_state"] = False
        
        # S5 activation logic
        if state in ("S2", "S3") and euphoria_cool_passed and s5_hyst["current_state"]:
            state = "S5"
            flags["s5_active"] = True
            flags["reentry_signal"] = True
        else:
            flags["s5_active"] = False
            flags["reentry_signal"] = False

        scores = {
            "trend_integrity": trend_healthy,
            "trend_strength": trend_strength,
            "continuation_quality": continuation,
            "absorption_score": cont_block.get("absorption_score", 0.0),
            "channel_penalty": cont_block.get("channel_penalty", 0.0),
            "euphoria_curve": euphoria,
            # S5
            "cooldown_integrity": s5.get("cooldown_integrity", 0.0),
            "reentry_readiness": s5.get("reentry_readiness", 0.0),
            # S2
            "support_persistence": s2_scores.get("support_persistence", 0.0),
            "reaction_quality": s2_scores.get("reaction_quality", 0.0),
            "close_persistence": s2_scores.get("close_persistence", 0.0),
            "absorption_wicks": s2_scores.get("absorption_wicks", 0.0),
            "ema_alignment": ema_alignment,
            "volatility_coherence": volatility_coherence,
            "sr_reclaim_score": sr_reclaim_score,
        }
        # Calculate highest close for chandelier (last 20 bars)
        highest_close = max(closes[-20:]) if len(closes) >= 20 else closes[-1]
        levels = {"ema20": ema20[-1], "ema50": ema50[-1], "highest_close": highest_close}
        sup_payload = {
            "current_support": s2.get("current_support"),
            "order": s2.get("order"),
            "halo": s2.get("halo"),
        }
        return {"state": state, "scores": scores, "flags": flags, "levels": levels, "supports": sup_payload, "s2_meta": s2.get("meta")}

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

                # Compute scores/state
                ss = self._score_and_state(contract, chain, features)
                payload = self._unified_payload(ss["state"], features)
                payload["scores"] = ss["scores"]
                payload["flag"] = ss["flags"]
                payload["levels"].update(ss["levels"])
                if ss.get("supports"):
                    payload["supports"] = ss["supports"]
                # Update emergency exit block
                payload = self._update_emergency_exit(payload, features, contract, chain)

                # Write snapshot to features.uptrend_engine (overwrite live snapshot)
                new_features = dict(features)
                prev = new_features.get("uptrend_engine") or {}
                payload["previous_state"] = prev.get("state")
                payload["previous_t0"] = prev.get("t0")
                # Handle AVWAP anchor on S1 transition
                prev_state = str(prev.get("state") or "")
                curr_state = str(ss["state"]) or ""
                meta = dict(new_features.get("uptrend_engine_meta") or {})
                if curr_state == "S1" and prev_state != "S1":
                    last_bar = self._latest_close_1h(contract, chain)
                    if last_bar.get("ts"):
                        meta["avwap_flip_anchor_ts"] = last_bar["ts"]
                # Compute current AVWAP if anchor exists
                anchor_ts = meta.get("avwap_flip_anchor_ts")
                if anchor_ts:
                    avwap_val = self._compute_avwap_current(contract, chain, str(anchor_ts))
                    if avwap_val is not None:
                        payload.setdefault("levels", {})["avwap_flip"] = avwap_val
                        payload.setdefault("meta", {})["avwap_flip_anchor_ts"] = anchor_ts
                # Update hysteresis state in meta
                meta["hysteresis"] = hysteresis
                new_features["uptrend_engine_meta"] = meta
                new_features["uptrend_engine"] = payload
                self.sb.table("lowcap_positions").update({"features": new_features}).eq("id", pid).execute()
                updated += 1

                # Emit specific state events on transitions
                prev_state = str(prev.get("state") or "")
                curr_state = str(payload.get("state") or "")
                event_payload = {"token_contract": contract, "chain": chain, "ts": now.isoformat(), "payload": payload}
                if curr_state == "S1" and prev_state != "S1":
                    self._emit_event("s1_breakout", event_payload)
                if curr_state in ("S2", "S3") and prev_state not in ("S2", "S3"):
                    self._emit_event("s2_support_touch", event_payload)
                if curr_state == "S3" and prev_state != "S3":
                    self._emit_event("s3_sr_reclaim", event_payload)
                # Euphoria on/off
                if payload.get("flag", {}).get("euphoria_building") and not (prev.get("flag", {}) or {}).get("euphoria_building"):
                    self._emit_event("s4_euphoria_on", event_payload)
                if (prev.get("flag", {}) or {}).get("euphoria_building") and not payload.get("flag", {}).get("euphoria_building"):
                    self._emit_event("s4_euphoria_off", event_payload)
                # S5 reentry on/off
                if payload.get("flag", {}).get("s5_active") and not (prev.get("flag", {}) or {}).get("s5_active"):
                    self._emit_event("s5_reentry_on", event_payload)
                if (prev.get("flag", {}) or {}).get("s5_active") and not payload.get("flag", {}).get("s5_active"):
                    self._emit_event("s5_reentry_off", event_payload)
            except Exception as e:
                logger.debug("uptrend_engine skipped position: %s", e)
        logger.info("Uptrend engine updated %d positions", updated)
        return updated


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    UptrendEngine().run()


if __name__ == "__main__":
    main()


