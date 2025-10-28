from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from supabase import create_client, Client  # type: ignore
from src.intelligence.lowcap_portfolio_manager.utils.resample import resample_15m_to_1h


logger = logging.getLogger(__name__)


def _ema_series(vals: List[float], span: int) -> List[float]:
    if not vals:
        return []
    alpha = 2.0 / (span + 1)
    out = [vals[0]]
    for v in vals[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def _rsi(values: List[float], period: int = 14) -> float:
    if len(values) <= period:
        return 50.0
    gains: List[float] = []
    losses: List[float] = []
    for i in range(len(values) - period, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(0.0, ch))
        losses.append(max(0.0, -ch))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period or 1e-9
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _zscore(window: List[float], value: float) -> float:
    import statistics

    if len(window) < 5:
        return 0.0
    mean = statistics.fmean(window)
    sd = statistics.pstdev(window) or 1.0
    return (value - mean) / sd


def _wilder_ema(prev: float, new: float, period: int) -> float:
    return (prev * (period - 1) + new) / period


def _atr_wilder(bars: List[Dict[str, Any]], period: int = 14) -> float:
    if len(bars) < 2:
        return 0.0
    trs: List[float] = []
    prev_c = bars[0]["c"]
    for b in bars[1:]:
        tr = max(b["h"] - b["l"], abs(b["h"] - prev_c), abs(prev_c - b["l"]))
        trs.append(tr)
        prev_c = b["c"]
    if not trs:
        return 0.0
    atr = sum(trs[: period]) / max(1, min(period, len(trs)))
    for tr in trs[period:]:
        atr = _wilder_ema(atr, tr, period)
    return atr


def _adx_wilder(bars: List[Dict[str, Any]], period: int = 14) -> float:
    # bars: list of dict with o,h,l,c
    n = len(bars)
    if n < period + 2:
        return 0.0
    # True range series
    trs: List[float] = []
    plus_dm: List[float] = []
    minus_dm: List[float] = []
    for i in range(1, n):
        up_move = bars[i]["h"] - bars[i - 1]["h"]
        down_move = bars[i - 1]["l"] - bars[i]["l"]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)
        tr = max(
            bars[i]["h"] - bars[i]["l"],
            abs(bars[i]["h"] - bars[i - 1]["c"]),
            abs(bars[i - 1]["c"] - bars[i]["l"]),
        )
        trs.append(tr)
    # Wilder smoothing
    atr = sum(trs[: period]) / period
    pdi = 0.0
    mdi = 0.0
    pdm = sum(plus_dm[: period]) / period
    mdm = sum(minus_dm[: period]) / period
    if atr > 0:
        pdi = 100.0 * (pdm / atr)
        mdi = 100.0 * (mdm / atr)
    dx_vals: List[float] = []
    dx_vals.append(100.0 * (abs(pdi - mdi) / max(pdi + mdi, 1e-9)))
    for i in range(period, len(trs)):
        atr = _wilder_ema(atr, trs[i], period)
        pdm = _wilder_ema(pdm, plus_dm[i], period)
        mdm = _wilder_ema(mdm, minus_dm[i], period)
        pdi = 100.0 * (pdm / max(atr, 1e-9))
        mdi = 100.0 * (mdm / max(atr, 1e-9))
        dx_vals.append(100.0 * (abs(pdi - mdi) / max(pdi + mdi, 1e-9)))
    # ADX = Wilder EMA of DX
    if not dx_vals:
        return 0.0
    adx = sum(dx_vals[: period]) / period if len(dx_vals) >= period else sum(dx_vals) / len(dx_vals)
    for dx in dx_vals[period:]:
        adx = _wilder_ema(adx, dx, period)
    return adx


def _build_15m_from_1m(closes_1m: List[float], times_1m: List[str]) -> List[Dict[str, Any]]:
    # Construct naive 15m bars (o,h,l,c) by grouping 15 1m closes
    fifteen: List[Dict[str, Any]] = []
    bucket: List[float] = []
    bucket_t0: Optional[str] = None
    for i, px in enumerate(closes_1m):
        ts = times_1m[i]
        if bucket_t0 is None:
            bucket_t0 = ts
        bucket.append(px)
        if len(bucket) == 15:
            o = bucket[0]
            h = max(bucket)
            l = min(bucket)
            c = bucket[-1]
            fifteen.append({"t0": bucket_t0, "o": o, "h": h, "l": l, "c": c})
            bucket = []
            bucket_t0 = None
    return fifteen


def _atr_15m(bars: List[Dict[str, Any]], period: int = 14) -> float:
    if len(bars) < 2:
        return 0.0
    trs: List[float] = []
    prev_c = bars[0]["c"]
    for b in bars[1:]:
        tr = max(b["h"] - b["l"], abs(b["h"] - prev_c), abs(prev_c - b["l"]))
        trs.append(tr)
        prev_c = b["c"]
    if not trs:
        return 0.0
    # Wilder smoothing
    atr = sum(trs[: period]) / max(1, min(period, len(trs)))
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _swing_pivots(vals: List[float]) -> Tuple[List[int], List[int]]:
    highs: List[int] = []
    lows: List[int] = []
    for i in range(2, len(vals) - 2):
        v = vals[i]
        if v > vals[i - 1] and v > vals[i - 2] and v > vals[i + 1] and v > vals[i + 2]:
            highs.append(i)
        if v < vals[i - 1] and v < vals[i - 2] and v < vals[i + 1] and v < vals[i + 2]:
            lows.append(i)
    return highs, lows


def _divergence(price_vals: List[float], rsi_vals: List[float]) -> str:
    ph, pl = _swing_pivots(price_vals)
    rh, rl = _swing_pivots(rsi_vals)
    # Prefer 3‑pivot confirmation when available; fallback to 2 pivots
    def last_three(idxs: List[int]) -> Optional[Tuple[int, int, int]]:
        if len(idxs) < 3:
            return None
        return idxs[-3], idxs[-2], idxs[-1]

    def last_two(idxs: List[int]) -> Optional[Tuple[int, int]]:
        if len(idxs) < 2:
            return None
        return idxs[-2], idxs[-1]

    # Bearish: price HH..HH while RSI LH..LH (3 pivots) or HH vs LH (2 pivots)
    # Bullish: price LL..LL while RSI HL..HL (3 pivots) or LL vs HL (2 pivots)
    try:
        h3 = last_three(ph)
        rh3 = last_three(rh)
        if h3 and rh3:
            p_a, p_b, p_c = price_vals[h3[0]], price_vals[h3[1]], price_vals[h3[2]]
            r_a, r_b, r_c = rsi_vals[rh3[0]], rsi_vals[rh3[1]], rsi_vals[rh3[2]]
            if (p_a < p_b < p_c) and (r_a > r_b > r_c):
                return "bear"
        l3 = last_three(pl)
        rl3 = last_three(rl)
        if l3 and rl3:
            p_a, p_b, p_c = price_vals[l3[0]], price_vals[l3[1]], price_vals[l3[2]]
            r_a, r_b, r_c = rsi_vals[rl3[0]], rsi_vals[rl3[1]], rsi_vals[rl3[2]]
            if (p_a > p_b > p_c) and (r_a < r_b < r_c):
                return "bull"
        # Fallback to 2‑pivot logic
        h2 = last_two(ph)
        rh2 = last_two(rh)
        if h2 and rh2:
            p1, p2 = price_vals[h2[0]], price_vals[h2[1]]
            r1, r2 = rsi_vals[rh2[0]], rsi_vals[rh2[1]]
            if p2 > p1 and r2 < r1:
                return "bear"
        l2 = last_two(pl)
        rl2 = last_two(rl)
        if l2 and rl2:
            p1, p2 = price_vals[l2[0]], price_vals[l2[1]]
            r1, r2 = rsi_vals[rl2[0]], rsi_vals[rl2[1]]
            if p2 < p1 and r2 > r1:
                return "bull"
    except Exception:
        pass
    return "none"


class TATracker:
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

                # Pull 1m prices (72h window or more if available)
                since_1m = (now - timedelta(hours=72)).isoformat()
                rows_1m = (
                    self.sb.table("lowcap_price_data_1m")
                    .select("timestamp, price_native, price_usd")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .gte("timestamp", since_1m)
                    .order("timestamp", desc=False)
                    .execute()
                    .data
                    or []
                )
                closes_1m: List[float] = []
                times_1m: List[str] = []
                for r in rows_1m:
                    px = float(r.get("price_native") or r.get("price_usd") or 0.0)
                    if px > 0:
                        closes_1m.append(px)
                        times_1m.append(str(r.get("timestamp")))
                # Real 15m OHLC (for RSI/VO_z/ATR and EMA_mid)
                rows_15m = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("timestamp, open_native, high_native, low_native, close_native, volume")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .eq("timeframe", "15m")
                    .lte("timestamp", now.isoformat())
                    .order("timestamp", desc=False)
                    .limit(200)
                    .execute()
                    .data
                    or []
                )
                if len(rows_15m) < 30:
                    # Not enough 15m history to compute stable VO_z; skip position gracefully
                    continue
                closes_15m = [float(r.get("close_native") or 0.0) for r in rows_15m]
                opens_15m = [float(r.get("open_native") or 0.0) for r in rows_15m]
                highs_15m = [float(r.get("high_native") or 0.0) for r in rows_15m]
                lows_15m = [float(r.get("low_native") or 0.0) for r in rows_15m]
                vols_15m = [float(r.get("volume") or 0.0) for r in rows_15m]

                # RSI(14) on 15m
                rsi_val = _rsi(closes_15m, 14)

                vo_z = _zscore(vols_15m[-30:] if len(vols_15m) >= 30 else vols_15m, vols_15m[-1] if vols_15m else 0.0)

                # ATR(14) on 15m (from real OHLC)
                bars_15m = [{"o": o, "h": h, "l": l, "c": c} for o, h, l, c in zip(opens_15m, highs_15m, lows_15m, closes_15m)]
                atr_15m = _atr_15m(bars_15m, 14)

                # Prefer real 1h OHLC; fallback to 15m→1h resample if missing
                rows_1h = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("timestamp, open_native, high_native, low_native, close_native, volume")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .eq("timeframe", "1h")
                    .lte("timestamp", now.isoformat())
                    .order("timestamp", desc=False)
                    .limit(200)
                    .execute()
                    .data
                    or []
                )
                if rows_1h:
                    bars_1h = [
                        {
                            "t0": datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00")),
                            "o": float(r.get("open_native") or 0.0),
                            "h": float(r.get("high_native") or 0.0),
                            "l": float(r.get("low_native") or 0.0),
                            "c": float(r.get("close_native") or 0.0),
                            "v": float(r.get("volume") or 0.0),
                        }
                        for r in rows_1h
                    ]
                else:
                    bars_1h = resample_15m_to_1h(rows_15m)
                ema20_1h = _ema_series([b["c"] for b in bars_1h], 20)
                ema50_1h = _ema_series([b["c"] for b in bars_1h], 50)
                ema20_1h_val = ema20_1h[-1] if ema20_1h else (closes_15m[-1] if closes_15m else 0.0)
                ema50_1h_val = ema50_1h[-1] if ema50_1h else (closes_15m[-1] if closes_15m else 0.0)
                atr_1h = _atr_wilder(bars_1h, 14) if bars_1h else 0.0
                adx_1h = _adx_wilder(bars_1h, 14) if bars_1h else 0.0

                # VO_z(1h) using log-volume EWMA (N=64), winsorize and cap [-4,+6]
                import math, statistics
                v1h = [max(0.0, float(b.get("v") or 0.0)) for b in bars_1h]
                if v1h:
                    log_v = [math.log(1.0 + v) for v in v1h]
                    # Winsorize 2/98 over trailing window
                    def winsorize(arr: List[float]) -> List[float]:
                        if len(arr) < 10:
                            return arr
                        s = sorted(arr)
                        lo_idx = max(0, int(0.02 * len(s)) - 1)
                        hi_idx = min(len(s) - 1, int(0.98 * len(s)))
                        lo, hi = s[lo_idx], s[hi_idx]
                        return [min(max(x, lo), hi) for x in arr]
                    log_v_win = winsorize(log_v)
                    # EWMA mean/var
                    N = 64
                    alpha = 2.0 / (N + 1)
                    mu = log_v_win[0]
                    var = 0.0
                    for x in log_v_win[1:]:
                        prev_mu = mu
                        mu = alpha * x + (1 - alpha) * mu
                        var = (1 - alpha) * (var + alpha * (x - prev_mu) * (x - mu))
                    sd = math.sqrt(max(var, 1e-12))
                    vo_z_1h = (log_v_win[-1] - mu) / (sd if sd > 0 else 1.0)
                    vo_z_1h = max(-4.0, min(6.0, vo_z_1h))
                    # Cluster-30 helper for S1 diagnostics
                    def cluster_true(zs: List[float]) -> bool:
                        window = zs[-30:] if len(zs) >= 30 else zs
                        return (sum(1 for z in window if z >= 2.0) >= 3) or (sum(max(0.0, z) for z in window) >= 6.0)
                    vo_z_cluster_1h = cluster_true([ (lv - mu) / (sd if sd>0 else 1.0) for lv in log_v_win ])
                else:
                    vo_z_1h = 0.0
                    vo_z_cluster_1h = False

                # EMA_long(1m) and consec_below (fallback to 15m proxy if 1m insufficient)
                ema_long: float
                consec_below: int
                if len(closes_1m) >= 60:
                    ema_long_series = _ema_series(closes_1m[-120:], 60)
                    ema_long = ema_long_series[-1] if ema_long_series else closes_1m[-1]
                    consec_below = 0
                    for v in reversed(closes_1m[-120:]):
                        if v < ema_long:
                            consec_below += 1
                        else:
                            break
                else:
                    # 15m proxy for EMA_long ≈ 60m → span ≈ 4 on 15m
                    ema_long_series_15 = _ema_series(closes_15m, 4)
                    ema_long = ema_long_series_15[-1] if ema_long_series_15 else closes_15m[-1]
                    consec_below = 0
                    for v in reversed(closes_15m[-40:]):
                        if v < ema_long:
                            consec_below += 1
                        else:
                            break

                # EMA_mid(15m) and break flag
                ema_mid_series = _ema_series(closes_15m, 55)
                ema_mid = ema_mid_series[-1] if ema_mid_series else closes_15m[-1]
                ema_mid_break = closes_15m[-1] < ema_mid

                # OBV (15m using true 15m volume) and slope z-per-bar over small window
                # Build OBV
                obv_series: List[float] = []
                acc = 0.0
                # Align closes_15m length to vols_15m if available
                L = min(len(closes_15m), len(vols_15m)) if vols_15m else len(closes_15m)
                pxs = closes_15m[-L:]
                vxs = vols_15m[-L:] if vols_15m else [0.0] * L
                for i in range(L):
                    if i == 0:
                        obv_series.append(0.0)
                        continue
                    if pxs[i] > pxs[i - 1]:
                        acc += vxs[i]
                    elif pxs[i] < pxs[i - 1]:
                        acc -= vxs[i]
                    obv_series.append(acc)
                # slope over window (mode window default = 4)
                win = min(6, len(obv_series))
                if win >= 3:
                    xs = list(range(win))
                    ys = obv_series[-win:]
                    xbar = sum(xs) / win
                    ybar = sum(ys) / win
                    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
                    den = sum((x - xbar) ** 2 for x in xs) or 1.0
                    slope = num / den
                    slope_window = [obv_series[i] - obv_series[i - 1] for i in range(len(obv_series) - win + 1, len(obv_series))]
                    slope_z_per_bar = _zscore(slope_window if slope_window else [0.0], slope) / max(1.0, float(win))
                else:
                    slope_z_per_bar = 0.0

                # RSI divergence classification using pivots on price and RSI(14)
                # Build RSI history from closes to match pivots
                rsi_series: List[float] = []
                for k in range(max(15, len(closes_15m) - 60), len(closes_15m)):
                    rsi_series.append(_rsi(closes_15m[: k + 1], 14))
                if len(rsi_series) >= 10:
                    div = _divergence(closes_15m[-len(rsi_series):], rsi_series)
                else:
                    div = "none"

                # Pillars
                obv_rising = slope_z_per_bar >= 0.05
                vo_moderate = vo_z >= 0.3
                rsi_bull_div = div in ("bull", "hidden_bull")
                pillars_cnt = int(obv_rising) + int(vo_moderate) + int(rsi_bull_div)

                ta = {
                    "rsi": {"value": rsi_val, "divergence": div, "lookback_bars": 14},
                    "obv": {"value": obv_series[-1] if obv_series else 0.0, "slope_z_per_bar": slope_z_per_bar, "divergence": "none", "window_bars": win},
                    "volume": {"vo_z_15m": vo_z, "vo_z_1h": vo_z_1h, "vo_z_cluster_1h": vo_z_cluster_1h, "window_bars": 30},
                    "ema": {"ema_long_1m": ema_long, "consec_below_ema_long": consec_below, "ema_mid_15m": ema_mid, "ema_mid_15m_break": ema_mid_break, "ema20_1h": ema20_1h_val, "ema50_1h": ema50_1h_val},
                    "atr": {"atr_15m": atr_15m, "atr_1h": atr_1h},
                    "adx": {"adx_1h": adx_1h},
                    "pillars": {"obv_rising": obv_rising, "vo_moderate": vo_moderate, "rsi_bull_div": rsi_bull_div, "count": pillars_cnt},
                    "updated_at": now.isoformat(),
                }

                new_features = dict(features)
                new_features["ta"] = ta
                self.sb.table("lowcap_positions").update({"features": new_features}).eq("id", pid).execute()
                updated += 1
            except Exception as e:
                logger.debug("ta_tracker skipped position: %s", e)
        logger.info("TA tracker updated %d positions", updated)
        return updated


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    TATracker().run()


if __name__ == "__main__":
    main()


