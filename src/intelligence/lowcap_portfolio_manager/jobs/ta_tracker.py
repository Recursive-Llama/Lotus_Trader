from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

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

# Performance thresholds for logging
QUERY_WARN_SECONDS = 5.0
QUERY_CRITICAL_SECONDS = 30.0
DEFAULT_CHUNK_SIZE = 100

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
    def __init__(self, timeframe: str = "1h") -> None:
        """
        Initialize TA Tracker.
        
        Args:
            timeframe: Timeframe to process ("1m", "15m", "1h", "4h")
        """
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.timeframe = timeframe
        # Map timeframe to suffix (e.g., "1m" -> "_1m", "1h" -> "_1h")
        self.ta_suffix = f"_{timeframe}"

    def _active_positions_chunked(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Generator[Dict[str, Any], None, None]:
        """Yield positions in chunks to prevent timeout on large datasets.
        
        IMPORTANT: Does NOT select 'features' - that's read per-position when writing.
        This pattern prevents bulk-reading large JSONB columns that cause timeouts.
        See: write_features_token_geometry() for the correct pattern.
        
        Args:
            chunk_size: Number of positions to fetch per query (default 100)
            
        Yields:
            Position dictionaries one at a time
        """
        offset = 0
        total_fetched = 0
        start_time = time.time()
        
        while True:
            query_start = time.time()
            res = (
                self.sb.table("lowcap_positions")
                .select("id,token_contract,token_chain,timeframe")  # NO features!
                .eq("timeframe", self.timeframe)
                .in_("status", ["watchlist", "active"])
                .range(offset, offset + chunk_size - 1)
                .execute()
            )
            query_time = time.time() - query_start
            
            if query_time > QUERY_WARN_SECONDS:
                logger.warning(
                    "Slow position query: chunk %d-%d took %.2fs",
                    offset, offset + chunk_size, query_time
                )
            
            batch = res.data or []
            if not batch:
                break
                
            total_fetched += len(batch)
            for p in batch:
                yield p
            
            offset += chunk_size
            
            # Safety: max 2000 positions (same as old limit)
            if total_fetched >= 2000:
                logger.warning("Hit position limit (2000), stopping")
                break
        
        total_time = time.time() - start_time
        if total_time > QUERY_CRITICAL_SECONDS:
            logger.error(
                "CRITICAL: Fetching %d positions took %.2fs - investigate query performance",
                total_fetched, total_time
            )
        elif total_fetched > 0:
            logger.debug("Fetched %d positions in %.2fs", total_fetched, total_time)

    def _write_features_ta(self, position_id: str, ta: Dict[str, Any]) -> None:
        """Write TA to features using per-position read-modify-write pattern.
        
        This avoids bulk-reading features in _active_positions() which causes timeouts.
        Pattern matches write_features_token_geometry() in spiral/persist.py.
        """
        try:
            row = (
                self.sb.table("lowcap_positions")
                .select("features")
                .eq("id", position_id)
                .limit(1)
                .execute()
                .data or []
            )
            features = (row[0].get("features") if row else {}) or {}
            features["ta"] = ta
            self.sb.table("lowcap_positions").update({"features": features}).eq("id", position_id).execute()
        except Exception as e:
            logger.error("Failed to write TA for position %s: %s", position_id, e)
            raise

    def run(self) -> int:
        now = datetime.now(timezone.utc)
        updated = 0
        skipped = 0
        errors = 0
        
        for p in self._active_positions_chunked():
            pid = p.get("id")
            contract = p.get("token_contract")
            chain = p.get("token_chain")
            
            try:
                # Timeframe-specific OHLC
                # IMPORTANT: Supabase has a default row limit of 1000 rows.
                # We order DESC to get the NEWEST rows first, then reverse in Python.
                # This ensures we always have the most recent data for EMA calculation.
                rows_tf = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
                    .eq("token_contract", contract)
                    .eq("chain", chain)
                    .eq("timeframe", self.timeframe)
                    .lte("timestamp", now.isoformat())
                    .order("timestamp", desc=True)  # DESC to get newest first
                    .limit(1000)  # Supabase caps at 1000 anyway
                    .execute()
                    .data
                    or []
                )
                # Reverse to chronological order (oldest first) for EMA calculation
                rows_tf = list(reversed(rows_tf))
                # Minimum bars required varies by timeframe
                # 1m: 333 bars minimum (matches backfill minimum, ~5.5 hours)
                # 15m: 288 bars (~3 days)
                # 1h: 72 bars (~3 days)
                # 4h: 18 bars (~3 days)
                min_bars_map = {"1m": 333, "15m": 288, "1h": 72, "4h": 18}
                min_bars = min_bars_map.get(self.timeframe, 72)
                if len(rows_tf) < min_bars:
                    logger.debug(f"Skipping {self.timeframe} position {contract}: only {len(rows_tf)} bars, need {min_bars}")
                    skipped += 1
                    continue  # require at least min_bars for this timeframe
                bars_tf = [
                    {
                        "t0": datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00")),
                        "o": float(r.get("open_usd") or 0.0),
                        "h": float(r.get("high_usd") or 0.0),
                        "l": float(r.get("low_usd") or 0.0),
                        "c": float(r.get("close_usd") or 0.0),
                        "v": float(r.get("volume") or 0.0),
                    }
                    for r in rows_tf
                ]
                ema20_tf = ema_series([b["c"] for b in bars_tf], 20)
                ema30_tf = ema_series([b["c"] for b in bars_tf], 30)
                ema50_tf = ema_series([b["c"] for b in bars_tf], 50)
                ema60_tf = ema_series([b["c"] for b in bars_tf], 60)
                ema144_tf = ema_series([b["c"] for b in bars_tf], 144)
                ema250_tf = ema_series([b["c"] for b in bars_tf], 250)
                ema333_tf = ema_series([b["c"] for b in bars_tf], 333)

                ema20_tf_val = ema20_tf[-1] if ema20_tf else (bars_tf[-1]["c"] if bars_tf else 0.0)
                ema30_tf_val = ema30_tf[-1] if ema30_tf else (bars_tf[-1]["c"] if bars_tf else 0.0)
                ema50_tf_val = ema50_tf[-1] if ema50_tf else (bars_tf[-1]["c"] if bars_tf else 0.0)
                atr_series_tf = atr_series_wilder(bars_tf, 14)
                atr_tf = atr_series_tf[-1] if atr_series_tf else 0.0
                adx_series_tf = adx_series_wilder(bars_tf, 14)
                adx_tf = adx_series_tf[-1] if adx_series_tf else 0.0

                # VO_z(timeframe) using log-volume EWMA (N=64), winsorize and cap [-4,+6]
                import math, statistics
                v_tf = [max(0.0, float(b.get("v") or 0.0)) for b in bars_tf]
                if v_tf:
                    log_v = [math.log(1.0 + v) for v in v_tf]
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
                    vo_z_tf = (log_v_win[-1] - mu) / (sd if sd > 0 else 1.0)
                    vo_z_tf = max(-4.0, min(6.0, vo_z_tf))
                    # Cluster-30 helper for S1 diagnostics
                    def cluster_true(zs: List[float]) -> bool:
                        window = zs[-30:] if len(zs) >= 30 else zs
                        return (sum(1 for z in window if z >= 2.0) >= 3) or (sum(max(0.0, z) for z in window) >= 6.0)
                    vo_z_cluster_tf = cluster_true([ (lv - mu) / (sd if sd>0 else 1.0) for lv in log_v_win ])
                else:
                    vo_z_tf = 0.0
                    vo_z_cluster_tf = False

                # RSI(timeframe) series and slopes
                closes_tf = [b["c"] for b in bars_tf]
                rsi_series_tf: List[float] = []
                for k in range(max(15, len(closes_tf) - 60), len(closes_tf)):
                    rsi_series_tf.append(rsi(closes_tf[: k + 1], 14))
                rsi_tf = rsi_series_tf[-1] if rsi_series_tf else 50.0
                rsi_slope_10 = lin_slope(rsi_series_tf, 10) if rsi_series_tf else 0.0

                # EMA slopes (%/bar) and accelerations - using shared utilities
                ema20_slope = ema_slope_normalized(ema20_tf, window=10)
                ema60_slope = ema_slope_normalized(ema60_tf, window=10)
                ema144_slope = ema_slope_normalized(ema144_tf, window=10)
                ema250_slope = ema_slope_normalized(ema250_tf, window=10)
                ema333_slope = ema_slope_normalized(ema333_tf, window=10)

                # Slope deltas (acceleration)
                d_ema60_slope = ema_slope_delta(ema60_tf, window=10, lag=10)
                d_ema144_slope = ema_slope_delta(ema144_tf, window=10, lag=10)
                d_ema250_slope = ema_slope_delta(ema250_tf, window=10, lag=10)
                d_ema333_slope = ema_slope_delta(ema333_tf, window=10, lag=10)

                # Separations and dsep
                sep_fast = ( (ema20_tf[-1] if ema20_tf else 0.0) - (ema60_tf[-1] if ema60_tf else 1e-9) ) / max(ema60_tf[-1] if ema60_tf else 1e-9, 1e-9)
                sep_mid = ( (ema60_tf[-1] if ema60_tf else 0.0) - (ema144_tf[-1] if ema144_tf else 1e-9) ) / max(ema144_tf[-1] if ema144_tf else 1e-9, 1e-9)
                if len(ema60_tf) >= 6 and len(ema144_tf) >= 6 and len(ema20_tf) >= 6:
                    sep_fast_prev = ( (ema20_tf[-6]) - (ema60_tf[-6]) ) / max(ema60_tf[-6], 1e-9)
                    sep_mid_prev = ( (ema60_tf[-6]) - (ema144_tf[-6]) ) / max(ema144_tf[-6], 1e-9)
                else:
                    sep_fast_prev = sep_fast
                    sep_mid_prev = sep_mid
                dsep_fast_5 = sep_fast - sep_fast_prev
                dsep_mid_5 = sep_mid - sep_mid_prev

                # ATR helpers
                atr_norm_tf = atr_tf / max(ema50_tf_val, 1e-9)
                import statistics as _stats
                atr_mean_20 = (_stats.fmean(atr_series_tf[-20:]) if len(atr_series_tf) >= 20 else atr_tf) if atr_series_tf else atr_tf
                atr_peak_10 = (max(atr_series_tf[-10:]) if len(atr_series_tf) >= 10 else atr_tf) if atr_series_tf else atr_tf

                # ADX slope over last 10 bars
                adx_slope_10 = lin_slope(adx_series_tf, 10) if adx_series_tf else 0.0

                # Build TA dict with timeframe-specific keys
                ta = {
                    "ema": {
                        f"ema20{self.ta_suffix}": ema20_tf_val,
                        f"ema30{self.ta_suffix}": ema30_tf_val,
                        f"ema50{self.ta_suffix}": ema50_tf_val,
                        f"ema60{self.ta_suffix}": ema60_tf[-1] if ema60_tf else ema20_tf_val,
                        f"ema144{self.ta_suffix}": ema144_tf[-1] if ema144_tf else ema20_tf_val,
                        f"ema250{self.ta_suffix}": ema250_tf[-1] if ema250_tf else ema20_tf_val,
                        f"ema333{self.ta_suffix}": ema333_tf[-1] if ema333_tf else ema20_tf_val,
                    },
                    "ema_slopes": {
                        f"ema20_slope{self.ta_suffix}": ema20_slope,
                        f"ema60_slope{self.ta_suffix}": ema60_slope,
                        f"ema144_slope{self.ta_suffix}": ema144_slope,
                        f"ema250_slope{self.ta_suffix}": ema250_slope,
                        f"ema333_slope{self.ta_suffix}": ema333_slope,
                        f"d_ema60_slope{self.ta_suffix}": d_ema60_slope,
                        f"d_ema144_slope{self.ta_suffix}": d_ema144_slope,
                        f"d_ema250_slope{self.ta_suffix}": d_ema250_slope,
                        f"d_ema333_slope{self.ta_suffix}": d_ema333_slope,
                    },
                    "separations": {
                        f"sep_fast{self.ta_suffix}": sep_fast,
                        f"sep_mid{self.ta_suffix}": sep_mid,
                        f"dsep_fast_5{self.ta_suffix}": dsep_fast_5,
                        f"dsep_mid_5{self.ta_suffix}": dsep_mid_5,
                    },
                    "atr": {
                        f"atr{self.ta_suffix}": atr_tf,
                        f"atr_norm{self.ta_suffix}": atr_norm_tf,
                        f"atr_mean_20{self.ta_suffix}": atr_mean_20,
                        f"atr_peak_10{self.ta_suffix}": atr_peak_10,
                    },
                    "momentum": {
                        f"rsi{self.ta_suffix}": rsi_tf,
                        f"rsi_slope_10{self.ta_suffix}": rsi_slope_10,
                        f"adx{self.ta_suffix}": adx_tf,
                        f"adx_slope_10{self.ta_suffix}": adx_slope_10,
                    },
                    "volume": {
                        f"vo_z{self.ta_suffix}": vo_z_tf,
                        f"vo_z_cluster{self.ta_suffix}": vo_z_cluster_tf
                    },
                    "meta": {
                        f"source{self.ta_suffix}": self.timeframe,
                        "updated_at": now.isoformat()
                    },
                }

                # Per-position write (reads features only for this position, not bulk)
                self._write_features_ta(pid, ta)
                updated += 1
                
            except Exception as e:
                errors += 1
                logger.error(
                    "TA Tracker failed for %s/%s (timeframe=%s): %s",
                    contract, chain, self.timeframe, e
                )
                # Continue to next position - one failure shouldn't stop the batch
                continue
                
        logger.info(
            "TA Tracker (%s) complete: updated=%d, skipped=%d, errors=%d",
            self.timeframe, updated, skipped, errors
        )
        return updated


def main(timeframe: str = "1h") -> None:
    """
    Main entry point for TA Tracker.
    
    Args:
        timeframe: Timeframe to process ("1m", "15m", "1h", "4h")
    """
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    TATracker(timeframe=timeframe).run()


if __name__ == "__main__":
    main()


