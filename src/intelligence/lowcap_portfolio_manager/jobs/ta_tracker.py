from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from supabase import create_client, Client  # type: ignore

from src.intelligence.lowcap_portfolio_manager.jobs.ta_utils import (
    ema_series,
    lin_slope,
    ema_slope_normalized,
    ema_slope_delta,
    atr_series_wilder,
    adx_series_wilder,
    rsi,
    zscore,
    wilder_ema,
)

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility (if anything imports these directly)
_ema_series = ema_series
_lin_slope = lin_slope
_rsi = rsi
_zscore = zscore
_wilder_ema = wilder_ema
_atr_series_wilder = atr_series_wilder
_adx_series_wilder = adx_series_wilder


# Functions removed - now imported from ta_utils.py
# Keeping _atr_wilder as it's a convenience wrapper
def _atr_wilder(bars: List[Dict[str, Any]], period: int = 14) -> float:
    """Convenience wrapper for single ATR value."""
    series = atr_series_wilder(bars, period)
    return series[-1] if series else 0.0


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
                # Strict 1h-only OHLC
                rows_1h = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("timestamp, open_native, high_native, low_native, close_native, volume")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .eq("timeframe", "1h")
                    .lte("timestamp", now.isoformat())
                    .order("timestamp", desc=False)
                    .limit(400)
                    .execute()
                    .data
                    or []
                )
                if len(rows_1h) < 72:
                    continue  # require at least 72 1h bars
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
                ema20_1h = ema_series([b["c"] for b in bars_1h], 20)
                ema50_1h = ema_series([b["c"] for b in bars_1h], 50)
                ema60_1h = ema_series([b["c"] for b in bars_1h], 60)
                ema144_1h = ema_series([b["c"] for b in bars_1h], 144)
                ema250_1h = ema_series([b["c"] for b in bars_1h], 250)
                ema333_1h = ema_series([b["c"] for b in bars_1h], 333)

                ema20_1h_val = ema20_1h[-1] if ema20_1h else (bars_1h[-1]["c"] if bars_1h else 0.0)
                ema50_1h_val = ema50_1h[-1] if ema50_1h else (bars_1h[-1]["c"] if bars_1h else 0.0)
                atr_series_1h = atr_series_wilder(bars_1h, 14)
                atr_1h = atr_series_1h[-1] if atr_series_1h else 0.0
                adx_series_1h = adx_series_wilder(bars_1h, 14)
                adx_1h = adx_series_1h[-1] if adx_series_1h else 0.0

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

                # RSI(1h) series and slopes
                closes_1h = [b["c"] for b in bars_1h]
                rsi_series_1h: List[float] = []
                for k in range(max(15, len(closes_1h) - 60), len(closes_1h)):
                    rsi_series_1h.append(rsi(closes_1h[: k + 1], 14))
                rsi_1h = rsi_series_1h[-1] if rsi_series_1h else 50.0
                rsi_slope_10 = lin_slope(rsi_series_1h, 10) if rsi_series_1h else 0.0

                # EMA slopes (%/bar) and accelerations - using shared utilities
                ema20_slope = ema_slope_normalized(ema20_1h, window=10)
                ema60_slope = ema_slope_normalized(ema60_1h, window=10)
                ema144_slope = ema_slope_normalized(ema144_1h, window=10)
                ema250_slope = ema_slope_normalized(ema250_1h, window=10)
                ema333_slope = ema_slope_normalized(ema333_1h, window=10)

                # Slope deltas (acceleration)
                d_ema60_slope = ema_slope_delta(ema60_1h, window=10, lag=10)
                d_ema144_slope = ema_slope_delta(ema144_1h, window=10, lag=10)
                d_ema250_slope = ema_slope_delta(ema250_1h, window=10, lag=10)
                d_ema333_slope = ema_slope_delta(ema333_1h, window=10, lag=10)

                # Separations and dsep
                sep_fast = ( (ema20_1h[-1] if ema20_1h else 0.0) - (ema60_1h[-1] if ema60_1h else 1e-9) ) / max(ema60_1h[-1] if ema60_1h else 1e-9, 1e-9)
                sep_mid = ( (ema60_1h[-1] if ema60_1h else 0.0) - (ema144_1h[-1] if ema144_1h else 1e-9) ) / max(ema144_1h[-1] if ema144_1h else 1e-9, 1e-9)
                if len(ema60_1h) >= 6 and len(ema144_1h) >= 6 and len(ema20_1h) >= 6:
                    sep_fast_prev = ( (ema20_1h[-6]) - (ema60_1h[-6]) ) / max(ema60_1h[-6], 1e-9)
                    sep_mid_prev = ( (ema60_1h[-6]) - (ema144_1h[-6]) ) / max(ema144_1h[-6], 1e-9)
                else:
                    sep_fast_prev = sep_fast
                    sep_mid_prev = sep_mid
                dsep_fast_5 = sep_fast - sep_fast_prev
                dsep_mid_5 = sep_mid - sep_mid_prev

                # ATR helpers
                atr_norm_1h = atr_1h / max(ema50_1h_val, 1e-9)
                import statistics as _stats
                atr_mean_20 = (_stats.fmean(atr_series_1h[-20:]) if len(atr_series_1h) >= 20 else atr_1h) if atr_series_1h else atr_1h
                atr_peak_10 = (max(atr_series_1h[-10:]) if len(atr_series_1h) >= 10 else atr_1h) if atr_series_1h else atr_1h

                # ADX slope over last 10 bars
                adx_slope_10 = lin_slope(adx_series_1h, 10) if adx_series_1h else 0.0

                ta = {
                    "ema": {
                        "ema20_1h": ema20_1h_val,
                        "ema50_1h": ema50_1h_val,
                        "ema60_1h": ema60_1h[-1] if ema60_1h else ema20_1h_val,
                        "ema144_1h": ema144_1h[-1] if ema144_1h else ema20_1h_val,
                        "ema250_1h": ema250_1h[-1] if ema250_1h else ema20_1h_val,
                        "ema333_1h": ema333_1h[-1] if ema333_1h else ema20_1h_val,
                    },
                    "ema_slopes": {
                        "ema20_slope": ema20_slope,
                        "ema60_slope": ema60_slope,
                        "ema144_slope": ema144_slope,
                        "ema250_slope": ema250_slope,
                        "ema333_slope": ema333_slope,
                        "d_ema60_slope": d_ema60_slope,
                        "d_ema144_slope": d_ema144_slope,
                        "d_ema250_slope": d_ema250_slope,
                        "d_ema333_slope": d_ema333_slope,
                    },
                    "separations": {
                        "sep_fast": sep_fast,
                        "sep_mid": sep_mid,
                        "dsep_fast_5": dsep_fast_5,
                        "dsep_mid_5": dsep_mid_5,
                    },
                    "atr": {
                        "atr_1h": atr_1h,
                        "atr_norm_1h": atr_norm_1h,
                        "atr_mean_20": atr_mean_20,
                        "atr_peak_10": atr_peak_10,
                    },
                    "momentum": {
                        "rsi_1h": rsi_1h,
                        "rsi_slope_10": rsi_slope_10,
                        "adx_1h": adx_1h,
                        "adx_slope_10": adx_slope_10,
                    },
                    "volume": {"vo_z_1h": vo_z_1h, "vo_z_cluster_1h": vo_z_cluster_1h},
                    "meta": {"source_1h": "1h", "updated_at": now.isoformat()},
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


