#!/usr/bin/env python3
"""
Backtest UptrendEngineV2 safely (no production writes).
- Runs geometry once (no charts), TA per-hour (time-filtered), and engine per-hour (time-filtered)
- Produces a results JSON and two charts (verification + state timeline)
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv  # type: ignore

# Production jobs
from src.intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import GeometryBuilder
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v2 import UptrendEngineV2
from src.intelligence.lowcap_portfolio_manager.jobs.ta_tracker import (
    _ema_series,
    _lin_slope,
    _atr_series_wilder,
    _adx_series_wilder,
    _rsi,
)

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_valid_price_row(row: Dict[str, Any]) -> bool:
    """Check if a row has valid (non-zero) price data."""
    close_val = float(row.get("close_native") or 0.0)
    return close_val > 0


def _forward_fill_prices(rows_1h: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Forward-fill missing or zero OHLC prices from the last valid price.
    Only fills AFTER we've encountered at least one valid price.
    Returns a copy of rows with filled prices (rows before first valid remain unchanged).
    """
    filled_rows = []
    last_valid_price = None
    
    for r in rows_1h:
        filled_r = dict(r)
        
        # Check if close is valid (non-zero and positive)
        close_val = float(r.get("close_native") or 0.0)
        if close_val > 0:
            last_valid_price = close_val
        
        # If we have a last valid price, forward-fill zero/missing values
        # (only forward-fill AFTER we've seen at least one valid price)
        if last_valid_price and last_valid_price > 0:
            if float(r.get("open_native") or 0.0) <= 0:
                filled_r["open_native"] = last_valid_price
            if float(r.get("high_native") or 0.0) <= 0:
                filled_r["high_native"] = last_valid_price
            if float(r.get("low_native") or 0.0) <= 0:
                filled_r["low_native"] = last_valid_price
            if float(r.get("close_native") or 0.0) <= 0:
                filled_r["close_native"] = last_valid_price
        
        filled_rows.append(filled_r)
    
    return filled_rows


def _filter_valid_bars(rows_1h: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out bars with zero/missing prices. Only return rows with valid prices.
    This ensures we don't process invalid data.
    """
    return [r for r in rows_1h if _is_valid_price_row(r)]


class SupabaseCtx:
    def __init__(self) -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)

    def load_position_features(self, contract: str, chain: str) -> Dict[str, Any]:
        res = (
            self.sb.table("lowcap_positions")
            .select("id, token_contract, token_chain, features")
            .eq("token_contract", contract)
            .eq("token_chain", chain)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise RuntimeError(f"No active position for {contract} on {chain}")
        return rows[0]

    def fetch_ohlc_1h_lte(self, contract: str, chain: str, until_iso: str, limit: int = 400) -> List[Dict[str, Any]]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", until_iso)
            .order("timestamp", desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows


def _build_ta_payload_from_rows(rows_1h: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build TA payload from OHLC rows. Assumes rows_1h has already been filtered
    to valid prices and forward-filled (so zeros should only exist before first valid).
    """
    # Filter to only valid price bars (skip any leading zeros that weren't filled)
    valid_rows = _filter_valid_bars(rows_1h)
    if len(valid_rows) < 72:
        return {}
    
    bars_1h = [
        {
            "t0": datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00")),
            "o": float(r.get("open_native") or 0.0),
            "h": float(r.get("high_native") or 0.0),
            "l": float(r.get("low_native") or 0.0),
            "c": float(r.get("close_native") or 0.0),
            "v": float(r.get("volume") or 0.0),
        }
        for r in valid_rows
    ]
    closes = [b["c"] for b in bars_1h]

    ema20_1h = _ema_series(closes, 20)
    ema50_1h = _ema_series(closes, 50)
    ema60_1h = _ema_series(closes, 60)
    ema144_1h = _ema_series(closes, 144)
    ema250_1h = _ema_series(closes, 250)
    ema333_1h = _ema_series(closes, 333)

    # Slopes (last-N linear regression)
    def slope(series: List[float], win: int) -> float:
        vals = [v for v in series if v is not None]
        return _lin_slope(vals, win) if vals else 0.0

    atr_series_1h = _atr_series_wilder(bars_1h, 14)
    adx_series_1h = _adx_series_wilder(bars_1h, 14)
    adx_1h = adx_series_1h[-1] if adx_series_1h else 0.0

    # VO_z (rough; simple zscore over log volume window)
    import math, statistics
    v1h = [max(0.0, float(b.get("v") or 0.0)) for b in bars_1h]
    log_v = [math.log(1.0 + v) for v in v1h] if v1h else []
    L = 64
    if len(log_v) >= L:
        window = log_v[-L:]
        mean = statistics.fmean(window)
        sd = statistics.pstdev(window) or 1.0
        vo_z_1h = (log_v[-1] - mean) / sd
    else:
        vo_z_1h = 0.0
    vo_z_cluster_1h = bool(vo_z_1h >= 2.0)

    ta = {
        "ema": {
            "ema20_1h": ema20_1h[-1] if ema20_1h else 0.0,
            "ema50_1h": ema50_1h[-1] if ema50_1h else 0.0,
            "ema60_1h": ema60_1h[-1] if ema60_1h else 0.0,
            "ema144_1h": ema144_1h[-1] if ema144_1h else 0.0,
            "ema250_1h": ema250_1h[-1] if ema250_1h else 0.0,
            "ema333_1h": ema333_1h[-1] if ema333_1h else 0.0,
        },
        "atr": {
            "atr_1h": atr_series_1h[-1] if atr_series_1h else 0.0,
            "atr_mean_20": sum(atr_series_1h[-20:]) / max(1, min(20, len(atr_series_1h))) if atr_series_1h else 0.0,
        },
        "momentum": {
            "adx_1h": adx_1h,
            "rsi_slope_10": slope([_rsi(closes[:i + 1], 14) for i in range(len(closes))], 10),
            "adx_slope_10": slope(adx_series_1h, 10) if adx_series_1h else 0.0,
        },
        "volume": {
            "vo_z_1h": vo_z_1h,
            "vo_z_cluster_1h": vo_z_cluster_1h,
        },
        "separations": {
            # sep_fast = (EMA20 − EMA60)/EMA60, sep_mid = (EMA60 − EMA144)/EMA144
            "sep_fast": ((ema20_1h[-1] - ema60_1h[-1]) / max(ema60_1h[-1], 1e-9)) if (ema20_1h and ema60_1h) else 0.0,
            "sep_mid": ((ema60_1h[-1] - ema144_1h[-1]) / max(ema144_1h[-1], 1e-9)) if (ema60_1h and ema144_1h) else 0.0,
            # dsep over 5 bars using simple difference of sep series
            "dsep_fast_5": 0.0,
            "dsep_mid_5": 0.0,
        },
        "ema_slopes": {
            "ema20_slope": slope(ema20_1h, 10),
            "ema60_slope": slope(ema60_1h, 10),
            "ema144_slope": slope(ema144_1h, 10),
            "ema250_slope": slope(ema250_1h, 10),
            "ema333_slope": slope(ema333_1h, 10),
            "d_ema60_slope": slope(ema60_1h, 5) - slope(ema60_1h, 10),
            "d_ema144_slope": slope(ema144_1h, 5) - slope(ema144_1h, 10),
            "d_ema250_slope": slope(ema250_1h, 5) - slope(ema250_1h, 10),
            "d_ema333_slope": slope(ema333_1h, 5) - slope(ema333_1h, 10),
        },
    }

    # Compute dsep over last 5 bars if possible
    def _sep_fast_series(e20: List[float], e60: List[float]) -> List[float]:
        out: List[float] = []
        for a, b in zip(e20, e60):
            if b and b != 0:
                out.append((a - b) / b)
            else:
                out.append(0.0)
        return out

    def _sep_mid_series(e60: List[float], e144: List[float]) -> List[float]:
        out: List[float] = []
        for a, b in zip(e60, e144):
            if b and b != 0:
                out.append((a - b) / b)
            else:
                out.append(0.0)
        return out

    sep_fast_series = _sep_fast_series(ema20_1h, ema60_1h)
    sep_mid_series = _sep_mid_series(ema60_1h, ema144_1h)
    if len(sep_fast_series) >= 6:
        ta["separations"]["dsep_fast_5"] = sep_fast_series[-1] - sep_fast_series[-6]
    if len(sep_mid_series) >= 6:
        ta["separations"]["dsep_mid_5"] = sep_mid_series[-1] - sep_mid_series[-6]

    return ta


class BacktestEngine(UptrendEngineV2):
    """Engine with time-filtered data access that analyzes in-memory features without DB writes."""

    def __init__(self, target_ts: datetime):
        super().__init__()
        self.target_ts = target_ts

    # Override data access to be <= target_ts
    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
        # Fetch multiple rows to find last valid price for forward-fill
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, low_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", self.target_ts.isoformat())
            .order("timestamp", desc=True)
            .limit(10)  # Fetch more to find valid price
            .execute()
            .data
            or []
        )
        
        if not rows:
            return {"ts": None, "close": 0.0, "low": 0.0}
        
        # Forward-fill: find last valid price
        last_valid_close = None
        last_valid_low = None
        for r in rows:
            close_val = float(r.get("close_native") or 0.0)
            low_val = float(r.get("low_native") or 0.0)
            if close_val > 0:
                if last_valid_close is None:
                    last_valid_close = close_val
                if low_val > 0 and last_valid_low is None:
                    last_valid_low = low_val
        
        r = rows[0]  # Most recent row
        close = float(r.get("close_native") or 0.0)
        low = float(r.get("low_native") or 0.0)
        
        # Use forward-filled values if current is zero
        if close <= 0 and last_valid_close:
            close = last_valid_close
        if low <= 0 and last_valid_low:
            low = last_valid_low
        
        return {"ts": str(r.get("timestamp")), "close": close, "low": low}

    def _last_two_closes_1h(self, contract: str, chain: str) -> List[Dict[str, Any]]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", self.target_ts.isoformat())
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
            .lte("timestamp", self.target_ts.isoformat())
            .order("timestamp", desc=False)
            .limit(300)
            .execute()
            .data
            or []
        )
        # Forward-fill missing/zero prices
        return _forward_fill_prices(rows)

    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 60) -> List[Dict[str, Any]]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", self.target_ts.isoformat())
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        rows.reverse()
        # Forward-fill missing/zero prices
        return _forward_fill_prices(rows)

    def analyze_single(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Replicate run() logic for one position, without DB writes or global scores_log writes."""
        # Read current TA and SR (use helper methods for consistency with production)
        sr_levels = self._read_sr_levels(features)
        ta = self._read_ta(features)
        if not sr_levels or not ta:
            # Not enough inputs
            return {"state": "S0", "payload": {}}

        now = self.target_ts
        prev_payload = dict((features.get("uptrend_engine") or {}))
        prev_state = str(prev_payload.get("state") or "")
        
        # Bootstrap: If first run (no prev_state), determine initial state using window-based price vs EMA333 check
        # NOTE: This matches production logic (uptrend_engine_v2.py lines 1065-1130)
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
                            # Otherwise → S3 (uptrend or neutral) - bootstrap to S3
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
                                return payload
                except Exception:
                    pass  # If bootstrap check fails, continue to default S0 below
            
            # Default to S0 if bootstrap didn't set S3
            if not prev_state or prev_state == "":
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
                    "diagnostics": {"bootstrap": "S0", "reason": "downtrend_or_insufficient_data"}
                })
                features["uptrend_engine"] = payload
                return payload
        
        # If we reach here, bootstrap is done (either S3 or S0 was set above)
        # Continue with normal state machine logic...
        
        # Initialize payload to None - will be set by S0/S1/S2/S3 logic
        payload = None
        
        # S1 detection: ONLY from S0 (not from S3 - once in S3, breakout already happened)
        # S3 can only exit to S0 (trend invalidation), never back to S1/S2
        if prev_state in ("", "S0"):
            s1 = self._detect_s1_breakout(ta)
            if s1.get("breakout"):
                closes2 = self._last_two_closes_1h(contract, chain)
                if len(closes2) >= 2:
                    px_breakout = float(closes2[0].get("close_native") or 0.0)
                    px_prev_close = float(closes2[1].get("close_native") or 0.0)
                elif len(closes2) == 1:
                    px_breakout = float(closes2[0].get("close_native") or 0.0)
                    px_prev_close = px_breakout
                else:
                    px_breakout = float((ta.get("ema") or {}).get("ema20_1h") or 0.0)
                s1_sr = self._cache_s1_artifacts(sr_levels, px_breakout, px_prev_close)
                # Freeze S0 baselines if present
                meta = dict(features.get("uptrend_engine_meta") or {})
                s0_baselines = dict(meta.get("s0") or {})
                if not s0_baselines:
                    s0_comp = self._compute_s0_compression_and_baselines(contract, chain, ta, features)
                    s0_baselines = s0_comp.get("baselines", {})
                # Cache last_support_below_breakout
                try:
                    recent_rows = self._fetch_recent_ohlc(contract, chain, limit=50)
                    lsb = self._select_last_support_below_breakout(sr_levels, recent_rows, px_breakout)
                except Exception:
                    lsb = float(s1_sr.get("base_sr_level") or 0.0)
                meta["s1"] = {
                    "base_sr_level": s1_sr.get("base_sr_level", 0.0),
                    "flipped_sr_levels": s1_sr.get("flipped_sr_levels", []),
                    "sr_flip_score": s1_sr.get("sr_flip_score", 0.0),
                    "breakout_price": px_breakout,
                    "breakout_ts": now.isoformat(),
                    "atr_norm_baseline": float(s0_baselines.get("atr_norm_baseline") or 0.0),
                    "sep_fast_start": float(s0_baselines.get("sep_fast_start") or 0.0),
                    "sep_mid_start": float(s0_baselines.get("sep_mid_start") or 0.0),
                    "adx_baseline": float(s0_baselines.get("adx_baseline") or 0.0),
                    "s0_compression_index": float(s0_baselines.get("compression_index") or 0.5),
                    "last_support_below_breakout": float(lsb or 0.0),
                }
                features["uptrend_engine_meta"] = meta
                s1_scores = self._compute_s1_scores(ta, float(s1_sr.get("sr_flip_score", 0.0)), px_breakout)
                bs_base = s1_scores.pop("breakout_strength_base", 0.0)
                s0_compression_index = float(meta["s1"].get("s0_compression_index") or 0.5)
                b_boost = 0.85 + 0.15 * s0_compression_index
                breakout_strength = max(0.0, min(1.0, bs_base * b_boost))
                payload = self._build_payload("S1", features, {
                    "flag": {"breakout_confirmed": True},
                    **s1_sr,
                    "scores": {"sr_flip_score": s1_sr.get("sr_flip_score", 0.0), "breakout_strength": breakout_strength, **s1_scores},
                })
                features["uptrend_engine"] = payload
                return payload
        
        # S2 management: ONLY from S0/S1/S2, NEVER from S3
        # S3 is operating regime - if S3 conditions fail, we go to S0 (trend end), not back to S2
        if prev_state != "S3":
            s2 = self._s2_manage(contract, chain, features)
            if s2.get("active"):
                meta_ro = dict(features.get("uptrend_engine_meta") or {})
                s1_ro = dict(meta_ro.get("s1") or {})
                base_sr_level = s1_ro.get("base_sr_level", 0.0)
                flipped_sr_levels = s1_ro.get("flipped_sr_levels", [])
                payload = self._build_payload("S2", features, {
                    "flag": {"uptrend_holding": s2.get("flags", {}).get("uptrend_holding", False)},
                    "scores": s2.get("scores", {}),
                    "base_sr_level": base_sr_level,
                    "flipped_sr_levels": flipped_sr_levels,
                })
                payload.setdefault("supports", {})
                payload["supports"].update({
                    "current_sr_level": s2.get("current_sr", 0.0),
                    "halo": s2.get("halo", 0.0),
                })
                # Persist updated meta from s2 in-memory
                features.update(s2.get("features", {}))
                features["uptrend_engine"] = payload
                return payload
            
            # S1 fakeout check before S3 (only if not in S3)
            meta_ro = dict(features.get("uptrend_engine_meta") or {})
            if meta_ro.get("s1") and self._check_s1_fakeout(contract, chain, features):
                try:
                    meta_ro.pop("s1", None)
                    meta_ro.pop("s2", None)
                    features["uptrend_engine_meta"] = meta_ro
                except Exception:
                    pass
                payload = self._build_payload("S0", features, {"flag": {"watch_only": True}, "diagnostics": {"s1_fakeout": True}})
                features["uptrend_engine"] = payload
                return payload

        # S3 → S0 transition: Emergency exit or persistent downtrend (8+ of 10 bars < EMA333)
        # NOTE: This matches production logic (uptrend_engine_v2.py lines 1232-1295)
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
                                        "ts": now.isoformat(),
                                        "break_time": now.isoformat(),
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
                            
                            features["uptrend_engine"] = payload
                            return payload
                except Exception:
                    pass  # If check fails, continue to S3 regime
        
        # S0 explicit stay: If in S0 and no S1 breakout, explicitly stay in S0 (don't fall through to S3)
        # NOTE: This matches production logic (uptrend_engine_v2.py lines 1297-1311)
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
            features["uptrend_engine"] = payload
            return payload
        
        # S3 regime: if not in S1/S2, not transitioning from S3, and not staying in S0, compute S3
        # NOTE: This matches production logic (uptrend_engine_v2.py lines 1313-1363)
        if payload is None:
        s3 = self._compute_s3_scores(contract, chain, features)
        if s3:
            payload = self._build_payload("S3", features, {"scores": s3.get("scores", {}), "diagnostics": s3.get("diagnostics", {})})
            payload["flags"] = s3.get("flags", {})
            # sr_context
            try:
                atr_1h = float((features.get("ta") or {}).get("atr", {}).get("atr_1h") or 0.0)
                last_px = self._latest_close_1h(contract, chain).get("close") or 0.0
                halo = max(0.5 * atr_1h, 0.03 * float(last_px)) if float(last_px) > 0 else 0.0
            except Exception:
                halo = 0.0
                meta_ro = dict(features.get("uptrend_engine_meta") or {})
                s1_ro = dict(meta_ro.get("s1") or {})
                base_sr_level = float(s1_ro.get("base_sr_level") or 0.0)
                flipped_sr_levels = list(s1_ro.get("flipped_sr_levels") or [])
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
                features["uptrend_engine"] = payload
                return payload

        # Default S0 fallback: if S3 computation failed or no S3 scores, default to S0
        # NOTE: This should rarely happen, but ensures we always return a payload
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
        features["uptrend_engine"] = payload
        return payload


def hourly_range(start: datetime, end: datetime) -> List[datetime]:
    out = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur = cur + timedelta(hours=1)
    return out


def generate_results_chart(results: List[Dict[str, Any]], contract: str, chain: str, sbx: SupabaseCtx) -> str:
    if not results:
        return ""
    
    # Extract data from results
    timestamps: List[datetime] = []
    prices: List[float] = []
    states: List[str] = []
    dx_buy_signals: List[Tuple[datetime, float, float]] = []  # (timestamp, price, dx_score) for actual DX buys
    dx_near_miss: List[Tuple[datetime, float, float]] = []  # (timestamp, price, dx_score) for near-miss DX (dx_flag=True but low DX)
    ox_sell_signals: List[Tuple[datetime, float, float]] = []  # (timestamp, price, ox_adj) for OX sell signals
    
    # Aggressiveness: assume Normal (A=0.5)
    A = 0.5
    tau_dx = 0.80 - 0.30 * A  # 0.65 for Normal
    tau_trim = 0.8 - 0.3 * A  # 0.65 for Normal
    
    for r in results:
        ts = r.get("analysis_ts")
        if not ts:
            continue
        ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        timestamps.append(ts_dt)
        prices.append(float(((r.get('levels') or {}).get('current_price')) or 0.0))
        states.append(str(r.get("state") or "S0"))
        
        # Extract scores and flags
        scores = r.get("scores") or {}
        flags = r.get("flags") or {}
        dx = float(scores.get("dx", 0.0))
        ox = float(scores.get("ox", 0.0))
        edx = float(scores.get("edx", 0.0))
        dx_flag = bool(flags.get("dx_flag", False))
        
        # DX buy signals: dx_flag=True AND DX >= threshold
        if dx_flag:
            if dx >= tau_dx:
                # Actual DX buy signal
                dx_buy_signals.append((ts_dt, prices[-1], dx))
            else:
                # Near miss: price in discount zone but DX not high enough
                dx_near_miss.append((ts_dt, prices[-1], dx))
        
        # OX sell signals: OX_adj > trim threshold
        # OX_adj = OX × (1 + 0.33×edx_boost) where edx_boost = max(0, min(0.5, edx - 0.5))
        edx_boost = max(0.0, min(0.5, edx - 0.5))
        ox_adj = ox * (1.0 + 0.33 * edx_boost)
        if ox_adj >= tau_trim:
            ox_sell_signals.append((ts_dt, prices[-1], ox_adj))
    
    if not timestamps:
        return ""
    
    # Fetch full OHLC data for EMAs
    if not timestamps:
        return ""
    last_ts = timestamps[-1]
    rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, last_ts.isoformat(), limit=400)
    if not rows_1h:
        return ""
    
    # Forward-fill missing/zero prices before building bars
    rows_1h_filled = _forward_fill_prices(rows_1h)
    
    # Build bar data
    bars_1h = [
        {
            "t0": datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00")),
            "c": float(r.get("close_native") or 0.0),
            "v": float(r.get("volume") or 0.0),
        }
        for r in rows_1h_filled
    ]
    closes = [b["c"] for b in bars_1h]
    bar_times = [b["t0"] for b in bars_1h]
    
    # Calculate EMAs (imported at top) - returns full-length list same as closes
    ema20_1h = _ema_series(closes, 20)
    ema30_1h = _ema_series(closes, 30)
    ema60_1h = _ema_series(closes, 60)
    ema144_1h = _ema_series(closes, 144)
    ema250_1h = _ema_series(closes, 250)
    ema333_1h = _ema_series(closes, 333)
    
    # Get S/R levels from payload sr_context or fallback to geometry features
    sr_levels: List[Dict[str, Any]] = []
    try:
        # First try payload sr_context
        if results:
            latest_result = results[-1]
            sr_context = latest_result.get("sr_context") or {}
            flipped = sr_context.get("flipped_sr_levels", [])
            base_sr = sr_context.get("base_sr_level")
            if base_sr:
                sr_levels.append({"price": float(base_sr), "type": "base", "strength": 20})
            for fl in flipped:
                if isinstance(fl, dict) and "level" in fl:
                    sr_levels.append({"price": float(fl["level"]), "type": "flipped", "strength": fl.get("score", 15)})
                elif isinstance(fl, (int, float)):
                    sr_levels.append({"price": float(fl), "type": "flipped", "strength": 15})
        
        # Fallback: fetch from geometry in DB features
        if not sr_levels:
            pos_row = sbx.load_position_features(contract, chain)
            features = pos_row.get("features") or {}
            geometry = features.get("geometry") or {}
            levels_obj = geometry.get("levels") or {}
            geom_sr = levels_obj.get("sr_levels", [])
            for sr in geom_sr[:10]:  # Top 10 levels
                price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                if price > 0:
                    sr_levels.append({"price": price, "type": "geometry", "strength": sr.get("strength", 10)})
    except Exception as e:
        logger.debug(f"Could not extract S/R levels: {e}")
    
    state_colors = {'S0': 'gray', 'S1': 'green', 'S2': 'blue', 'S3': 'orange'}
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]})
    
    # Plot price
    ax1.plot(bar_times, closes, 'b-', linewidth=1.5, alpha=0.8, label='Price (Native)')
    
    # Plot EMAs (now aligned to bar_times)
    ax1.plot(bar_times, ema20_1h, 'orange', linewidth=2, label='EMA 20', alpha=0.8)
    ax1.plot(bar_times, ema30_1h, 'yellow', linewidth=1.5, label='EMA 30', alpha=0.7)
    ax1.plot(bar_times, ema60_1h, 'purple', linewidth=2, label='EMA 60', alpha=0.8)
    ax1.plot(bar_times, ema144_1h, 'red', linewidth=2, label='EMA 144', alpha=0.8)
    ax1.plot(bar_times, ema250_1h, 'darkred', linewidth=2, label='EMA 250', alpha=0.8)
    ax1.plot(bar_times, ema333_1h, 'black', linewidth=3, label='EMA 333', alpha=0.9)
    
    # Plot S/R levels
    for sr in sr_levels:
        price = sr.get("price", 0.0)
        sr_type = sr.get("type", "unknown")
        color = 'cyan' if sr_type == 'base' else 'lightblue'
        ax1.axhline(y=price, color=color, linestyle='--', alpha=0.6, linewidth=1)
        ax1.text(bar_times[0], price, f"{sr_type}: {price:.6f}", fontsize=8, color=color, alpha=0.8, va='bottom')
    
    # Plot OX sell signals (sell zones)
    if ox_sell_signals:
        sell_times, sell_prices, sell_ox = zip(*ox_sell_signals)
        ax1.scatter(sell_times, sell_prices, color='red', s=120, marker='v', alpha=0.7, edgecolors='darkred', linewidths=2, label=f'OX Sell Zone ({len(ox_sell_signals)})', zorder=9)
    
    # Plot DX buy signals (actual buys - price in discount zone AND DX >= threshold)
    if dx_buy_signals:
        buy_times, buy_prices, buy_dx = zip(*dx_buy_signals)
        ax1.scatter(buy_times, buy_prices, color='lime', s=150, marker='^', alpha=0.9, edgecolors='darkgreen', linewidths=2, label=f'DX Buy Signal ({len(dx_buy_signals)})', zorder=10)
    
    # Plot DX near-miss (price in discount zone but DX < threshold)
    if dx_near_miss:
        miss_times, miss_prices, miss_dx = zip(*dx_near_miss)
        ax1.scatter(miss_times, miss_prices, color='orange', s=80, marker='o', alpha=0.6, edgecolors='darkorange', linewidths=1, label=f'DX Near Miss ({len(dx_near_miss)})', zorder=8)
    
    ax1.grid(True, alpha=0.3)
    # Get token ticker for title
    ticker = "UNKNOWN"
    try:
        pos_row = sbx.load_position_features(contract, chain)
        ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    except Exception:
        pass
    ax1.set_title(f'{ticker} Backtest - OX Sell Zones & DX Buy/Near-Miss Signals')
    ax1.set_ylabel('Price (Native)')
    ax1.legend(loc='upper left', fontsize=9)
    
    # State timeline
    mapping = {'S0': 0, 'S1': 1, 'S2': 2, 'S3': 3}
    ax2.plot(timestamps, [mapping.get(s, 0) for s in states], 'o-', linewidth=2, markersize=6, alpha=0.8)
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_yticklabels(['S0', 'S1', 'S2', 'S3'])
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel('State')
    ax2.set_xlabel('Time')
    
    # Format x-axis
    for ax in (ax1, ax2):
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Get token ticker for filename
    ticker = "UNKNOWN"
    try:
        pos_row = sbx.load_position_features(contract, chain)
        ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    except Exception:
        ticker = contract[:8]
    
    # Ensure v1 directory exists
    v1_dir = "backtester/v1"
    os.makedirs(v1_dir, exist_ok=True)
    
    out = f"{v1_dir}/backtest_results_{ticker}_{int(_now_utc().timestamp())}.png"
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return out


def main() -> None:
    import sys
    
    # Inputs: command line args or env vars
    if len(sys.argv) >= 2:
        # Usage: python3 backtest_uptrend_v2.py <token_ticker> [days]
        ticker = sys.argv[1].upper()
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 14
        
        # Look up contract from ticker
        sbx = SupabaseCtx()
        pos_res = (
            sbx.sb.table("lowcap_positions")
            .select("token_contract, token_chain")
            .eq("token_ticker", ticker)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if not pos_res.data:
            print(f"Token '{ticker}' not found in active positions")
            return
        contract = pos_res.data[0]["token_contract"]
        chain = pos_res.data[0]["token_chain"]
        print(f"Found {ticker}: {contract[:20]}... on {chain}")
    else:
        # Fallback to env vars
        contract = os.getenv("BT_CONTRACT", "")
        chain = os.getenv("BT_CHAIN", "solana")
        days = int(os.getenv("BT_DAYS", "14"))
        
        if not contract:
            print("Usage: python3 backtest_uptrend_v2.py <TOKEN_TICKER> [days]")
            print("   or: Set BT_CONTRACT, BT_CHAIN, BT_DAYS env vars")
            print("\nExample: python3 backtest_uptrend_v2.py DREAMS 14")
            return

    if 'sbx' not in locals():
        sbx = SupabaseCtx()

    # Align end_ts to last available DB bar to avoid plotting beyond data
    try:
        last_row = (
            sbx.sb.table("lowcap_price_data_ohlc")
            .select("timestamp")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if last_row:
            end_ts = datetime.fromisoformat(str(last_row[0]["timestamp"]).replace('Z', '+00:00'))
        else:
            end_ts = _now_utc()
    except Exception:
        end_ts = _now_utc()
    start_ts = end_ts - timedelta(days=days)

    print(f"\n=== Starting Backtest ===")
    print(f"Token: {contract[:20]}... on {chain}")
    print(f"Period: {days} days")
    print(f"From: {start_ts.isoformat()}")
    print(f"To: {end_ts.isoformat()}\n")

    # Step 1: Ensure geometry present (no charts)
    try:
        GeometryBuilder(generate_charts=False).build()
    except Exception as e:
        logger.warning(f"Geometry build failed or skipped: {e}")

    # Load initial features row (we will mutate a local copy only)
    pos_row = sbx.load_position_features(contract, chain)
    features: Dict[str, Any] = dict(pos_row.get("features") or {})
    if not features:
        features = {}

    # end_ts/start_ts already computed above

    results: List[Dict[str, Any]] = []

    # Step 2: Fetch all bars in window once
    all_bars = sbx.fetch_ohlc_1h_lte(contract, chain, end_ts.isoformat(), limit=400)
    if not all_bars:
        logger.error(f"No OHLC data found for {contract} on {chain}")
        return
    
    # Filter to window and extract timestamps
    bar_timestamps: List[datetime] = []
    for bar in all_bars:
        bar_ts = datetime.fromisoformat(str(bar["timestamp"]).replace('Z', '+00:00'))
        if start_ts <= bar_ts <= end_ts:
            bar_timestamps.append(bar_ts)
    
    if not bar_timestamps:
        logger.error(f"No bars in window {start_ts.isoformat()} to {end_ts.isoformat()}")
        return
    
    print(f"Found {len(bar_timestamps)} bars to simulate")
    print(f"First bar: {bar_timestamps[0].isoformat()}")
    print(f"Last bar: {bar_timestamps[-1].isoformat()}\n")

    # Step 3-4: Iterate actual bar timestamps (one analysis per real bar)
    # Skip warmup period: find first bar with enough VALID (non-zero) bars for TA (72 bars minimum)
    results: List[Dict[str, Any]] = []
    start_idx = 0
    for idx, bar_ts in enumerate(bar_timestamps):
        rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, bar_ts.isoformat(), limit=400)
        # Filter to only valid price bars (non-zero)
        valid_rows = _filter_valid_bars(rows_1h)
        if len(valid_rows) >= 72:
            start_idx = idx
            print(f"Skipping {idx} bars (warmup). Starting analysis from bar #{idx+1} ({bar_ts.isoformat()})")
            print(f"  Valid price bars available: {len(valid_rows)}/{len(rows_1h)}")
            break
    
    for bar_ts in bar_timestamps[start_idx:]:
        try:
            # Build TA features at bar_ts (fetch all bars up to this timestamp)
            rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, bar_ts.isoformat(), limit=400)
            
            # Filter to only valid price bars (non-zero), then forward-fill any gaps
            valid_rows = _filter_valid_bars(rows_1h)
            if len(valid_rows) < 72:
                continue

            # Forward-fill any remaining gaps (for sparse missing data within valid range)
            rows_1h_filled = _forward_fill_prices(rows_1h)

            ta = _build_ta_payload_from_rows(rows_1h_filled)
            if not ta:
                continue
            features["ta"] = ta

            # Analyze engine at bar_ts (in-memory)
            engine = BacktestEngine(bar_ts)
            payload = engine.analyze_single(contract, chain, features)
            # Get current price (should be valid since we filtered above)
            last_close = float(rows_1h_filled[-1].get("close_native") or 0.0) if rows_1h_filled else 0.0
            if last_close <= 0:
                # Skip if somehow we got an invalid price
                continue
            payload.setdefault("levels", {})["current_price"] = last_close
            payload["analysis_ts"] = bar_ts.isoformat()
            payload["contract"] = contract
            payload["chain"] = chain
            # Keep evolving features/meta in-memory
            features = dict(features)
            features["uptrend_engine"] = payload

            results.append(payload)
        except Exception as e:
            logger.debug(f"Backtest step failed at {bar_ts.isoformat()}: {e}")
            continue

    # Output artifacts (use ticker for naming)
    ticker = "UNKNOWN"
    try:
        pos_row = sbx.load_position_features(contract, chain)
        ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    except Exception:
        ticker = contract[:8]
    
    # Ensure v1 directory exists
    v1_dir = "backtester/v1"
    os.makedirs(v1_dir, exist_ok=True)
    
    out_json = f"{v1_dir}/backtest_results_v2_{ticker}_{int(end_ts.timestamp())}.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved results to {out_json}")

    chart_file = generate_results_chart(results, contract, chain, sbx)
    if chart_file:
        print(f"Results chart: {chart_file}")
    print(f"Done. Points: {len(results)}")


if __name__ == "__main__":
    main()
