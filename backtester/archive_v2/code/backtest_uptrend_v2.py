#!/usr/bin/env python3
"""
Backtest UptrendEngineV2 safely (no production writes).
- Runs geometry once (no charts), TA per-hour (time-filtered), and engine per-hour (time-filtered)
- Produces a results JSON and chart
"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv  # type: ignore

# Production jobs
from src.intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import GeometryBuilder
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v2 import UptrendEngineV2, Constants
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
    return float(row.get("close_native") or 0.0) > 0


def _forward_fill_prices(rows_1h: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Forward-fill missing or zero OHLC prices from the last valid price."""
    filled_rows = []
    last_valid_price = None
    
    for r in rows_1h:
        filled_r = dict(r)
        close_val = float(r.get("close_native") or 0.0)
        if close_val > 0:
            last_valid_price = close_val
        
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
    """Filter out bars with zero/missing prices."""
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
            .select("id, token_contract, token_chain, features, token_ticker")
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
    """Build TA payload from OHLC rows."""
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
    ema30_1h = _ema_series(closes, 30)
    ema50_1h = _ema_series(closes, 50)
    ema60_1h = _ema_series(closes, 60)
    ema144_1h = _ema_series(closes, 144)
    ema250_1h = _ema_series(closes, 250)
    ema333_1h = _ema_series(closes, 333)

    def slope(series: List[float], win: int) -> float:
        vals = [v for v in series if v is not None]
        return _lin_slope(vals, win) if vals else 0.0

    atr_series_1h = _atr_series_wilder(bars_1h, 14)
    adx_series_1h = _adx_series_wilder(bars_1h, 14)
    adx_1h = adx_series_1h[-1] if adx_series_1h else 0.0

    # VO_z calculation
    import math
    import statistics
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
            "ema30_1h": ema30_1h[-1] if ema30_1h else 0.0,
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
            "sep_fast": ((ema20_1h[-1] - ema60_1h[-1]) / max(ema60_1h[-1], 1e-9)) if (ema20_1h and ema60_1h) else 0.0,
            "sep_mid": ((ema60_1h[-1] - ema144_1h[-1]) / max(ema144_1h[-1], 1e-9)) if (ema60_1h and ema144_1h) else 0.0,
            "dsep_fast_5": 0.0,
            "dsep_mid_5": 0.0,
        },
        "ema_slopes": {
            "ema20_slope": slope(ema20_1h, 10),
            "ema30_slope": slope(ema30_1h, 10),
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

    # Compute dsep over last 5 bars
    def _sep_fast_series(e20: List[float], e60: List[float]) -> List[float]:
        return [((a - b) / b) if b and b != 0 else 0.0 for a, b in zip(e20, e60)]

    def _sep_mid_series(e60: List[float], e144: List[float]) -> List[float]:
        return [((a - b) / b) if b and b != 0 else 0.0 for a, b in zip(e60, e144)]

    sep_fast_series = _sep_fast_series(ema20_1h, ema60_1h)
    sep_mid_series = _sep_mid_series(ema60_1h, ema144_1h)
    if len(sep_fast_series) >= 6:
        ta["separations"]["dsep_fast_5"] = sep_fast_series[-1] - sep_fast_series[-6]
    if len(sep_mid_series) >= 6:
        ta["separations"]["dsep_mid_5"] = sep_mid_series[-1] - sep_mid_series[-6]

    return ta


class BacktestEngine(UptrendEngineV2):
    """Engine with time-filtered data access for backtesting."""

    def __init__(self, target_ts: datetime):
        super().__init__()
        self.target_ts = target_ts

    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, low_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", self.target_ts.isoformat())
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
            .data
            or []
        )
        
        if not rows:
            return {"ts": None, "close": 0.0, "low": 0.0}
        
        # Find last valid price for forward-fill
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
        
        r = rows[0]
        close = float(r.get("close_native") or 0.0)
        low = float(r.get("low_native") or 0.0)
        
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
        return _forward_fill_prices(rows)

    def _get_previous_ema_values(self, contract: str, chain: str, ta: Dict[str, Any]) -> Dict[str, float]:
        """Get EMA values from the previous bar for crossover detection."""
        try:
            # Fetch last 2 bars to compute previous bar's TA
            recent_rows = self._fetch_recent_ohlc(contract, chain, limit=2)
            if len(recent_rows) < 2:
                return {}
            
            # Use the second-to-last bar for previous values
            prev_bar = recent_rows[-2]
            prev_ts = datetime.fromisoformat(str(prev_bar["timestamp"]).replace('Z', '+00:00'))
            
            # Fetch bars up to previous timestamp to compute TA
            rows_prev = self._fetch_ohlc_since(contract, chain, (prev_ts - timedelta(days=30)).isoformat())
            rows_prev = [r for r in rows_prev if datetime.fromisoformat(str(r["timestamp"]).replace('Z', '+00:00')) <= prev_ts]
            
            if len(rows_prev) < 20:  # Need at least 20 bars for EMA20
                return {}
            
            # Build TA for previous bar
            ta_prev = _build_ta_payload_from_rows(rows_prev)
            if not ta_prev:
                return {}
            
            ema_prev = ta_prev.get("ema", {})
            return {
                "ema20": float(ema_prev.get("ema20_1h") or 0.0),
                "ema30": float(ema_prev.get("ema30_1h") or 0.0),
                "ema60": float(ema_prev.get("ema60_1h") or 0.0),
            }
        except Exception:
            return {}

    def analyze_single(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze one position at target_ts without DB writes."""
        sr_levels = self._read_sr_levels(features)
        ta = self._read_ta(features)
        if not sr_levels or not ta:
            return {"state": "S0", "payload": {}}

        now = self.target_ts
        prev_payload = dict((features.get("uptrend_engine") or {}))
        prev_state = str(prev_payload.get("state") or "")
        
        # Bootstrap: If first run, determine initial state
        if not prev_state or prev_state == "":
            ema = ta.get("ema", {})
            ema333 = float(ema.get("ema333_1h", 0.0))
            
            if ema333 <= 0:
                # Default to S0
                pass
            else:
                try:
                    recent_rows = self._fetch_recent_ohlc(contract, chain, limit=10)
                    if len(recent_rows) >= 10:
                        below_count = 0
                        for r in recent_rows[-10:]:
                            px = float(r.get("close_native", 0.0))
                            if px < ema333:
                                below_count += 1
                        
                        if below_count >= 8:
                            # Bootstrap to S0
                            pass
                        else:
                            # Bootstrap to S3
                            s3 = self._compute_s3_scores(contract, chain, features)
                            if s3:
                                payload = self._build_payload("S3", features, {
                                    "scores": s3.get("scores", {}),
                                    "diagnostics": s3.get("diagnostics", {}),
                                })
                                payload["flags"] = s3.get("flags", {})
                                # Add sr_context
                                try:
                                    atr_1h = float((ta.get("atr") or {}).get("atr_1h") or 0.0)
                                    last_px = float((ta.get("ema") or {}).get("ema20_1h") or 0.0)
                                    halo = max(0.5 * atr_1h, 0.03 * last_px) if last_px > 0 else 0.0
                                    flipped_sr = []
                                    for sr in sr_levels[:5]:
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
                    pass
            
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
                })
                features["uptrend_engine"] = payload
                return payload
        
        # Normal state machine logic
        payload = None
        
        # S1 detection: ONLY from S0
        # NEW EMA-based logic: EMA20/30 turn upwards
        if prev_state in ("", "S0"):
            ema_slopes = ta.get("ema_slopes", {})
            ema20_slope = float(ema_slopes.get("ema20_slope") or 0.0)
            ema30_slope = float(ema_slopes.get("ema30_slope") or 0.0)
            
            # S1 triggered when EMA20 OR EMA30 slope turns positive (turning upwards)
            ema_turning_up = (ema20_slope > 0.0) or (ema30_slope > 0.0)
            
            if ema_turning_up:
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
                
                # Store S1 artifacts for EMA-based transition
                meta = dict(features.get("uptrend_engine_meta") or {})
                ema = ta.get("ema", {})
                ema20_value = float(ema.get("ema20_1h") or 0.0)
                ema30_value = float(ema.get("ema30_1h") or 0.0)
                
                meta["s1"] = {
                    "breakout_price": px_breakout,
                    "breakout_ts": now.isoformat(),
                    "ema20_at_s1": ema20_value,
                    "ema30_at_s1": ema30_value,
                }
                features["uptrend_engine_meta"] = meta
                
                payload = self._build_payload("S1", features, {
                    "flag": {"breakout_confirmed": True},
                    "scores": {},
                })
                features["uptrend_engine"] = payload
                return payload
        
        # S1 → S2 transition: NEW EMA-based logic
        # Conditions: ALL must be met:
        #   1. EMA60 slope positive (trending up over 10 bars)
        #   2. EMA60 acceleration positive (J-shape: slope increasing, not n-shape)
        #   3. EMA20/30 cross above EMA60 (both must be above now, and at least one crossed)
        #   4. Price above EMA60
        if prev_state == "S1" and payload is None:
            ema = ta.get("ema", {})
            ema_slopes = ta.get("ema_slopes", {})
            last = self._latest_close_1h(contract, chain)
            current_price = last["close"]
            
            ema20 = float(ema.get("ema20_1h") or 0.0)
            ema30 = float(ema.get("ema30_1h") or 0.0)
            ema60 = float(ema.get("ema60_1h") or 0.0)
            ema60_slope = float(ema_slopes.get("ema60_slope") or 0.0)
            d_ema60_slope = float(ema_slopes.get("d_ema60_slope") or 0.0)  # Acceleration
            
            # Get previous bar EMAs for crossover detection
            prev_emas = self._get_previous_ema_values(contract, chain, ta)
            prev_ema20 = prev_emas.get("ema20", ema20)
            prev_ema30 = prev_emas.get("ema30", ema30)
            prev_ema60 = prev_emas.get("ema60", ema60)
            
            # Condition 1: EMA60 slope positive (trending up over 10 bars)
            ema60_slope_positive = ema60_slope > 0.0
            
            # Condition 2: EMA60 acceleration positive (J-shape: slope increasing)
            ema60_accelerating = d_ema60_slope > 0.0  # Positive acceleration = J-shape
            
            # Condition 3: EMA20/30 cross above EMA60 (both must be above now, and at least one crossed)
            ema20_above_ema60 = ema20 > ema60
            ema30_above_ema60 = ema30 > ema60
            ema20_crossed = ema20 > ema60 and prev_ema20 <= prev_ema60
            ema30_crossed = ema30 > ema60 and prev_ema30 <= prev_ema60
            ema_crossed_above = (ema20_above_ema60 and ema30_above_ema60) and (ema20_crossed or ema30_crossed)
            
            # Condition 4: Price above EMA60
            price_above_ema60 = current_price > ema60 if ema60 > 0 else False
            
            # Transition to S2 if ALL FOUR conditions met (including J-shape requirement)
            if ema60_slope_positive and ema60_accelerating and ema_crossed_above and price_above_ema60:
                # Store EMA60 as the retest level for S2 (only once at entry)
                meta = dict(features.get("uptrend_engine_meta") or {})
                s1_meta = dict(meta.get("s1") or {})
                if not s1_meta:
                    s1_meta = {}
                # Only set EMA60 if not already set (preserve first entry value)
                if "ema60_at_s2_entry" not in s1_meta:
                    s1_meta["ema60_at_s2_entry"] = ema60
                    # Also store as base_sr_level in S1 meta (required by _s2_manage)
                    s1_meta["base_sr_level"] = ema60
                ema60_entry = float(s1_meta.get("ema60_at_s2_entry", ema60))
                meta["s1"] = s1_meta
                features["uptrend_engine_meta"] = meta
                
                # Use EMA60 entry value as the base S/R level for S2 (static, not changing)
                payload = self._build_payload("S2", features, {
                    "flag": {"uptrend_holding": False},  # Will be set based on buy conditions
                    "scores": {},
                    "base_sr_level": ema60_entry,  # Use EMA60 entry value (static)
                    "flipped_sr_levels": [],
                })
                payload.setdefault("supports", {})
                payload["supports"].update({
                    "current_sr_level": ema60_entry,
                    "halo": max(0.03 * ema60_entry, 0.0),  # 3% halo for buy zone
                })
                features["uptrend_engine"] = payload
                return payload
            else:
                # Stay in S1
                payload = self._build_payload("S1", features, {
                    "flag": {"breakout_confirmed": True},
                    "scores": prev_payload.get("scores", {}),
                })
                features["uptrend_engine"] = payload
                return payload
        
        # S2 → S3 transition: ONLY from S2, requires price > EMA333 for 8+ of 10 candles + EMA slopes + momentum
        # NOTE: Must check BEFORE S2 stay check, otherwise S2 stay returns early and this never runs
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
                            px = float(r.get("close_native", 0.0))
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
                    payload = self._build_payload("S3", features, {
                        "scores": s3.get("scores", {}),
                        "diagnostics": s3.get("diagnostics", {}),
                    })
                    payload["flags"] = s3.get("flags", {})
                    # Add sr_context
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
                    try:
                        flipped_sr_levels.sort(key=lambda x: float(x.get("level") or 0.0), reverse=True)
                    except Exception:
                        pass
                    
                    payload["sr_context"] = {
                        "halo": halo,
                        "base_sr_level": base_sr_level,
                        "flipped_sr_levels": flipped_sr_levels,
                    }
                    features = s3.get("features", features)
                    features["uptrend_engine"] = payload
                    return payload
        
        # S2 management: For staying in S2 (S2→S2)
        # NEW EMA-based logic: Check if price is within 3% of EMA60 or retesting EMA60
        # ALSO compute TI/TS scores for S2→S3 transition and buy signal filtering
        if prev_state == "S2" and payload is None:
            meta_ro = dict(features.get("uptrend_engine_meta") or {})
            s1_ro = dict(meta_ro.get("s1") or {})
            if s1_ro:  # Only if we have S1 meta (legitimately in S2 state)
                # Get the EMA60 value from when we entered S2 (static, not current EMA60)
                ema60_entry = float(s1_ro.get("ema60_at_s2_entry") or 0.0)
                
                last = self._latest_close_1h(contract, chain)
                current_price = last["close"]
                
                # Check if price is within 3% of EMA60 entry (buy zone on the way up)
                # OR price is retesting EMA60 entry (within 3% below EMA60)
                if ema60_entry > 0:
                    distance_from_ema60 = abs(current_price - ema60_entry) / ema60_entry if ema60_entry > 0 else 999.0
                    within_3pct = distance_from_ema60 <= 0.03  # 3% tolerance
                    
                    # Buy signal: price within 3% of EMA60 entry (either above or below for retest)
                    uptrend_holding = within_3pct
                else:
                    uptrend_holding = False
                
                # Compute TI/TS scores using _s2_manage (needed for S2→S3 transition and buy signal filtering)
                s2_scores = self._s2_manage(contract, chain, features)
                ti_ts_scores = s2_scores.get("scores", {})
                
                # Use EMA60 entry value as the base S/R level (static, from entry)
                payload = self._build_payload("S2", features, {
                    "flag": {"uptrend_holding": uptrend_holding},
                    "scores": ti_ts_scores,  # Include TI/TS scores for S2→S3 and buy filtering
                    "base_sr_level": ema60_entry,  # Static EMA60 from entry
                    "flipped_sr_levels": [],
                })
                payload.setdefault("supports", {})
                payload["supports"].update({
                    "current_sr_level": ema60_entry,
                    "halo": max(0.03 * ema60_entry, 0.0),  # 3% halo
                })
                features.update(s2_scores.get("features", {}))
                features["uptrend_engine"] = payload
                return payload
            
            # S2 fakeout check: EMA20/30 cross back below EMA60 (before entering S3)
            # NOTE: Only check fakeout if we're staying in S2 (not transitioning to S3)
            if payload is not None and prev_state == "S2" and payload.get("state") == "S2":
                ema = ta.get("ema", {})
                ema20 = float(ema.get("ema20_1h") or 0.0)
                ema30 = float(ema.get("ema30_1h") or 0.0)
                ema60 = float(ema.get("ema60_1h") or 0.0)
                
                # Get previous bar EMAs for crossover detection
                prev_emas = self._get_previous_ema_values(contract, chain, ta)
                prev_ema20 = prev_emas.get("ema20", ema20)
                prev_ema30 = prev_emas.get("ema30", ema30)
                prev_ema60 = prev_emas.get("ema60", ema60)
                
                # Check if EMA20 or EMA30 crossed back below EMA60
                ema20_crossed_below = ema20 < ema60 and prev_ema20 >= prev_ema60
                ema30_crossed_below = ema30 < ema60 and prev_ema30 >= prev_ema60
                
                if ema20_crossed_below or ema30_crossed_below:
                    meta_ro = dict(features.get("uptrend_engine_meta") or {})
                    try:
                        meta_ro.pop("s1", None)
                        features["uptrend_engine_meta"] = meta_ro
                    except Exception:
                        pass
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "diagnostics": {"s2_fakeout": True, "reason": "ema_cross_below_60"}
                    })
                    features["uptrend_engine"] = payload
                    return payload

        # S3 → S0 transition: persistent downtrend
        if payload is None and prev_state == "S3":
            ema = ta.get("ema", {})
            ema333 = float(ema.get("ema333_1h", 0.0))
            if ema333 > 0:
                try:
                    recent_rows = self._fetch_recent_ohlc(contract, chain, limit=10)
                    if len(recent_rows) >= 10:
                        below_count = 0
                        for r in recent_rows[-10:]:
                            px = float(r.get("close_native", 0.0))
                            if px < ema333:
                                below_count += 1
                        
                        if below_count >= 8:
                            s0_comp = self._compute_s0_compression_and_baselines(contract, chain, ta, features)
                            last = self._latest_close_1h(contract, chain)
                            px = last["close"]
                            low_now = last["low"]
                            atr_1h = float((ta.get("atr") or {}).get("atr_1h") or 0.0)
                            halo = max(0.5 * atr_1h, 0.03 * px) if px > 0 else 0.0
                            
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
                            
                            meta = dict(features.get("uptrend_engine_meta") or {})
                            meta.pop("s1", None)
                            meta.pop("s2", None)
                            features["uptrend_engine_meta"] = meta
                            features["uptrend_engine"] = payload
                            return payload
                except Exception:
                    pass
        
        # S0 explicit stay
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
            features["uptrend_engine"] = payload
            return payload
        
        # S2 explicit stay: Already handled above (line 548), this shouldn't be reached
        # But keeping as fallback in case logic changes
        
        # S3 explicit stay: If in S3 and not transitioning to S0, stay in S3
        if payload is None and prev_state == "S3":
            s3 = self._compute_s3_scores(contract, chain, features)
            if s3:
                payload = self._build_payload("S3", features, {
                    "scores": s3.get("scores", {}),
                    "diagnostics": s3.get("diagnostics", {}),
                })
                payload["flags"] = s3.get("flags", {})
                # Add sr_context
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
                try:
                    flipped_sr_levels.sort(key=lambda x: float(x.get("level") or 0.0), reverse=True)
                except Exception:
                    pass
                
                payload["sr_context"] = {
                    "halo": halo,
                    "base_sr_level": base_sr_level,
                    "flipped_sr_levels": flipped_sr_levels,
                }
                features = s3.get("features", features)
                features["uptrend_engine"] = payload
                return payload
        
        # Default S0 fallback
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


def generate_results_chart(results: List[Dict[str, Any]], contract: str, chain: str, sbx: SupabaseCtx) -> str:
    """Generate visualization chart with price, EMAs, states, and signals."""
    if not results:
        return ""
    
    timestamps: List[datetime] = []
    prices: List[float] = []
    states: List[str] = []
    dx_buy_signals: List[Tuple[datetime, float, float]] = []
    dx_near_miss: List[Tuple[datetime, float, float]] = []
    ox_sell_signals: List[Tuple[datetime, float, float]] = []
    s2_buy_signals: List[Tuple[datetime, float, float]] = []  # S2 entry signals
    
    # Thresholds (Normal aggressiveness: A=0.5)
    A = 0.5
    tau_dx = 0.80 - 0.30 * A  # 0.65
    tau_trim = 0.8 - 0.3 * A  # 0.65
    
    # S2 entry thresholds (normal aggressiveness A=0.5)
    tau_integrity_base = 0.80 - (0.40 * A)  # 0.60
    tau_strength_base = 0.75 - (0.35 * A)   # 0.575 ≈ 0.58
    
    # Track breakout_strength from S1 (for threshold adjustment)
    current_breakout_strength = 0.0
    
    for r in results:
        ts = r.get("analysis_ts")
        if not ts:
            continue
        ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        timestamps.append(ts_dt)
        prices.append(float(((r.get('levels') or {}).get('current_price')) or 0.0))
        states.append(str(r.get("state") or "S0"))
        
        scores = r.get("scores") or {}
        # Handle both "flag" (S0/S1/S2) and "flags" (S3)
        flags = r.get("flags") or r.get("flag") or {}
        state = str(r.get("state") or "S0")
        
        # Track breakout_strength from S1
        if state == "S1":
            current_breakout_strength = float(scores.get("breakout_strength", 0.0))
        
        dx = float(scores.get("dx", 0.0))
        ox = float(scores.get("ox", 0.0))
        edx = float(scores.get("edx", 0.0))
        dx_flag = bool(flags.get("dx_flag", False))
        
        # S2 buy signals (NEW EMA-based: price within 3% of EMA60 or retesting)
        # Green stars: price within 3% of EMA60 (no TI/TS filter)
        # Yellow stars: price within 3% of EMA60 AND TI/TS meet thresholds for normal aggressiveness
        if state == "S2":
            uptrend_holding = bool(flags.get("uptrend_holding", False))
            if uptrend_holding:
                # Check TI/TS thresholds (Normal aggressiveness: A=0.5)
                trend_integrity = float(scores.get("trend_integrity", 0.0))
                trend_strength = float(scores.get("trend_strength", 0.0))
                
                tau_integrity_base = 0.80 - (0.40 * 0.5)  # 0.60
                tau_strength_base = 0.75 - (0.35 * 0.5)   # 0.575 ≈ 0.58
                
                # Adjust thresholds by breakout_strength if available
                breakout_boost = max(0.0, min(0.15, current_breakout_strength * 0.15))
                tau_integrity = tau_integrity_base - breakout_boost
                tau_strength = tau_strength_base - breakout_boost
                
                ti_ts_met = (trend_integrity >= tau_integrity) and (trend_strength >= tau_strength)
                
                # Store signal with flag: True = TI/TS met (yellow), False = no TI/TS (green)
                s2_buy_signals.append((ts_dt, prices[-1], ti_ts_met))
        
        # DX buy signals
        if dx_flag:
            if dx >= tau_dx:
                dx_buy_signals.append((ts_dt, prices[-1], dx))
            else:
                dx_near_miss.append((ts_dt, prices[-1], dx))
        
        # OX sell signals
        edx_boost = max(0.0, min(0.5, edx - 0.5))
        ox_adj = ox * (1.0 + 0.33 * edx_boost)
        if ox_adj >= tau_trim:
            ox_sell_signals.append((ts_dt, prices[-1], ox_adj))
    
    if not timestamps:
        return ""
    
    # Fetch OHLC data for EMAs
    last_ts = timestamps[-1]
    rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, last_ts.isoformat(), limit=400)
    if not rows_1h:
        return ""
    
    rows_1h_filled = _forward_fill_prices(rows_1h)
    bars_1h = [
        {
            "t0": datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00")),
            "c": float(r.get("close_native") or 0.0),
        }
        for r in rows_1h_filled
    ]
    closes = [b["c"] for b in bars_1h]
    bar_times = [b["t0"] for b in bars_1h]
    
    # Calculate EMAs
    ema20_1h = _ema_series(closes, 20)
    ema30_1h = _ema_series(closes, 30)
    ema60_1h = _ema_series(closes, 60)
    ema144_1h = _ema_series(closes, 144)
    ema250_1h = _ema_series(closes, 250)
    ema333_1h = _ema_series(closes, 333)
    
    # Get S/R levels from geometry AND from results
    sr_levels: List[Dict[str, Any]] = []
    seen_prices = set()  # Avoid duplicates
    
    # First, get geometry S/R levels from features (from first result or load fresh)
    try:
        if results:
            # Try to get geometry from first result's contract/chain
            first_result = results[0]
            test_contract = first_result.get("contract", contract)
            test_chain = first_result.get("chain", chain)
            pos_row = sbx.load_position_features(test_contract, test_chain)
            features_geom = dict(pos_row.get("features") or {})
            geometry = features_geom.get("geometry") or {}
            geom_levels = ((geometry.get("levels") or {}).get("sr_levels") or [])
            for geom_lvl in geom_levels:
                price = float(geom_lvl.get("price", geom_lvl.get("price_native_raw", 0.0)))
                if price > 0 and price not in seen_prices:
                    strength = float(geom_lvl.get("strength", 10))
                    sr_levels.append({"price": price, "type": "geometry", "strength": strength})
                    seen_prices.add(price)
    except Exception as e:
        logger.debug(f"Could not load geometry S/R levels: {e}")
    
    # Then add S/R levels from results (S2 stores EMA60, S3 stores in sr_context)
    try:
        for r in results:
            # Check sr_context (S3 state) - only add unique ones not from geometry
            sr_context = r.get("sr_context") or {}
            if sr_context:
                base_sr = sr_context.get("base_sr_level")
                if base_sr:
                    price = float(base_sr)
                    if price > 0 and price not in seen_prices:
                        sr_levels.append({"price": price, "type": "base", "strength": 20})
                        seen_prices.add(price)
                
                flipped = sr_context.get("flipped_sr_levels", [])
                for fl in flipped:
                    if isinstance(fl, dict) and "level" in fl:
                        price = float(fl["level"])
                        if price > 0 and price not in seen_prices:
                            sr_levels.append({"price": price, "type": "flipped", "strength": fl.get("score", 15)})
                            seen_prices.add(price)
            
            # Check levels.base_sr_level (S2 state) - EMA60 entry value
            levels = r.get("levels") or {}
            base_sr = levels.get("base_sr_level")
            if base_sr:
                price = float(base_sr)
                if price > 0 and price not in seen_prices:
                    # Only add EMA60 if it's significantly different from geometry levels (to avoid duplicates)
                    is_ema60 = True  # Assume this is EMA60 from S2
                    sr_levels.append({"price": price, "type": "ema60_s2", "strength": 15})
                    seen_prices.add(price)
    except Exception as e:
        logger.debug(f"Could not extract S/R levels from results: {e}")
    
    # Create chart
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]})
    
    # Plot price and EMAs
    ax1.plot(bar_times, closes, 'b-', linewidth=1.5, alpha=0.8, label='Price')
    ax1.plot(bar_times, ema20_1h, 'orange', linewidth=2, label='EMA 20', alpha=0.8)
    ax1.plot(bar_times, ema30_1h, 'yellow', linewidth=1.5, label='EMA 30', alpha=0.7)
    ax1.plot(bar_times, ema60_1h, 'purple', linewidth=2, label='EMA 60', alpha=0.8)
    ax1.plot(bar_times, ema144_1h, 'red', linewidth=2, label='EMA 144', alpha=0.8)
    ax1.plot(bar_times, ema250_1h, 'darkred', linewidth=2, label='EMA 250', alpha=0.8)
    ax1.plot(bar_times, ema333_1h, 'black', linewidth=3, label='EMA 333', alpha=0.9)
    
    # Find and plot state transitions on price chart
    prev_state = None
    state_transitions = []  # List of (timestamp, price, from_state, to_state)
    for r in results:
        state = str(r.get("state") or "S0")
        ts_str = r.get("analysis_ts")
        if not ts_str:
            continue
        try:
            ts_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            price = float(((r.get('levels') or {}).get('current_price')) or 0.0)
            if state != prev_state and prev_state is not None:
                state_transitions.append((ts_dt, price, prev_state, state))
            prev_state = state
        except Exception:
            pass
    
    # Plot state transition markers with different colors/shapes
    transition_colors = {
        ('S0', 'S1'): 'green',
        ('S1', 'S2'): 'blue',
        ('S2', 'S3'): 'orange',
        ('S3', 'S0'): 'red',
        ('S2', 'S0'): 'red',  # Fakeout
    }
    transition_markers = {
        ('S0', 'S1'): 'o',  # Circle for breakout
        ('S1', 'S2'): 's',  # Square for retest
        ('S2', 'S3'): 'D',  # Diamond for operating regime
        ('S3', 'S0'): 'X',  # X for exit
        ('S2', 'S0'): 'X',  # X for fakeout
    }
    
    labeled_transitions = set()
    for ts, price, from_state, to_state in state_transitions:
        key = (from_state, to_state)
        color = transition_colors.get(key, 'gray')
        marker = transition_markers.get(key, 'o')
        label = f'{from_state}→{to_state}' if key not in labeled_transitions else ''
        if key not in labeled_transitions:
            labeled_transitions.add(key)
        ax1.scatter(ts, price, color=color, s=200, marker=marker, 
                   edgecolors='black', linewidths=2, alpha=0.9, 
                   label=label, zorder=12)
    
    # Find ATL (lowest price in results) and plot it
    all_result_prices = [float(((r.get('levels') or {}).get('current_price')) or 0.0) for r in results if (r.get('levels') or {}).get('current_price')]
    if all_result_prices:
        atl_price = min(all_result_prices)
        ax1.axhline(y=atl_price, color='red', linestyle=':', linewidth=2, alpha=0.8, label='ATL')
        if len(bar_times) > 0:
            ax1.text(bar_times[-1], atl_price, f' ATL', verticalalignment='center', 
                    fontsize=9, color='red', alpha=0.9, weight='bold')
    
    # Plot S/R levels with scores (only geometry lines, no EMA60 base level)
    for sr in sr_levels:
        price = sr.get("price", 0.0)
        sr_type = sr.get("type", "unknown")
        score = sr.get("strength", 0)
        # Skip EMA60 S2 base level (not needed, fakeout is EMA cross)
        if sr_type == 'ema60_s2' or sr_type == 'base':
            continue
        # Colors: blue for geometry, blue for flipped
        color = 'blue'
        ax1.axhline(y=price, color=color, linestyle='--', alpha=0.6, linewidth=1)
        # Add score annotation (position at right edge of chart)
        if price > 0 and len(bar_times) > 0:
            ax1.text(bar_times[-1], price, f' {score}', verticalalignment='center', 
                    fontsize=8, color=color, alpha=0.8)
    
    # Plot signals
    if ox_sell_signals:
        sell_times, sell_prices, sell_ox = zip(*ox_sell_signals)
        ax1.scatter(sell_times, sell_prices, color='red', s=120, marker='v', alpha=0.7, 
                   edgecolors='darkred', linewidths=2, label=f'OX Sell ({len(ox_sell_signals)})', zorder=9)
    
    if dx_buy_signals:
        buy_times, buy_prices, buy_dx = zip(*dx_buy_signals)
        ax1.scatter(buy_times, buy_prices, color='lime', s=150, marker='^', alpha=0.9, 
                   edgecolors='darkgreen', linewidths=2, label=f'DX Buy ({len(dx_buy_signals)})', zorder=10)
    
    if dx_near_miss:
        miss_times, miss_prices, miss_dx = zip(*dx_near_miss)
        ax1.scatter(miss_times, miss_prices, color='orange', s=80, marker='o', alpha=0.6, 
                   edgecolors='darkorange', linewidths=1, label=f'DX Near Miss ({len(dx_near_miss)})', zorder=8)
    
    # S2 buy signals: Separate green (no TI/TS) and yellow (TI/TS met)
    s2_green_signals = [(t, p) for t, p, ti_ts in s2_buy_signals if not ti_ts]
    s2_yellow_signals = [(t, p) for t, p, ti_ts in s2_buy_signals if ti_ts]
    
    if s2_green_signals:
        s2_green_times, s2_green_prices = zip(*s2_green_signals)
        ax1.scatter(s2_green_times, s2_green_prices, color='green', s=120, marker='*', alpha=0.9, 
                   edgecolors='darkgreen', linewidths=2, label=f'S2 Buy (Green: {len(s2_green_signals)})', zorder=11)
    
    if s2_yellow_signals:
        s2_yellow_times, s2_yellow_prices = zip(*s2_yellow_signals)
        ax1.scatter(s2_yellow_times, s2_yellow_prices, color='yellow', s=120, marker='*', alpha=0.9, 
                   edgecolors='orange', linewidths=2, label=f'S2 Buy (Yellow: {len(s2_yellow_signals)})', zorder=11)
    
    ax1.grid(True, alpha=0.3)
    
    # Get ticker for title
    ticker = "UNKNOWN"
    try:
        pos_row = sbx.load_position_features(contract, chain)
        ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    except Exception:
        pass
    
    ax1.set_title(f'{ticker} Backtest - OX Sell Zones & DX Buy Signals')
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
    
    # Save chart
    v2_dir = "backtester/v2"
    os.makedirs(v2_dir, exist_ok=True)
    out = f"{v2_dir}/backtest_results_{ticker}_{int(_now_utc().timestamp())}.png"
    plt.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return out


def main() -> None:
    import sys
    
    # Get inputs
    if len(sys.argv) >= 2:
        ticker = sys.argv[1].upper()
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 14
        
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

    # Align end_ts to last available bar
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

    # Step 1: Ensure geometry present
    try:
        GeometryBuilder(generate_charts=False).build()
    except Exception as e:
        logger.warning(f"Geometry build failed or skipped: {e}")

    # Load initial features
    pos_row = sbx.load_position_features(contract, chain)
    features: Dict[str, Any] = dict(pos_row.get("features") or {})
    if not features:
        features = {}

    results: List[Dict[str, Any]] = []

    # Fetch all bars in window
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

    # Skip warmup period
    start_idx = 0
    for idx, bar_ts in enumerate(bar_timestamps):
        rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, bar_ts.isoformat(), limit=400)
        valid_rows = _filter_valid_bars(rows_1h)
        if len(valid_rows) >= 72:
            start_idx = idx
            print(f"Skipping {idx} bars (warmup). Starting from bar #{idx+1} ({bar_ts.isoformat()})")
            print(f"  Valid price bars: {len(valid_rows)}/{len(rows_1h)}")
            break
    
    # Run backtest per bar
    for bar_ts in bar_timestamps[start_idx:]:
        try:
            rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, bar_ts.isoformat(), limit=400)
            valid_rows = _filter_valid_bars(rows_1h)
            if len(valid_rows) < 72:
                continue

            rows_1h_filled = _forward_fill_prices(rows_1h)
            ta = _build_ta_payload_from_rows(rows_1h_filled)
            if not ta:
                continue
            features["ta"] = ta

            # Analyze engine at bar_ts
            engine = BacktestEngine(bar_ts)
            payload = engine.analyze_single(contract, chain, features)
            
            last_close = float(rows_1h_filled[-1].get("close_native") or 0.0) if rows_1h_filled else 0.0
            if last_close <= 0:
                continue
            
            payload.setdefault("levels", {})["current_price"] = last_close
            payload["analysis_ts"] = bar_ts.isoformat()
            payload["contract"] = contract
            payload["chain"] = chain
            
            # Store TA breakout detection conditions for debugging
            if ta:
                ema_slopes = ta.get("ema_slopes", {})
                seps = ta.get("separations", {})
                atr = ta.get("atr", {})
                vol = ta.get("volume", {})
                payload["_debug_s1_conditions"] = {
                    "ema20_slope": float(ema_slopes.get("ema20_slope", 0) or 0),
                    "dsep_fast_5": float(seps.get("dsep_fast_5", 0) or 0),
                    "atr_1h": float(atr.get("atr_1h", 0) or 0),
                    "atr_mean_20": float(atr.get("atr_mean_20", atr.get("atr_1h", 0)) or 0),
                    "atr_rising": float(atr.get("atr_1h", 0) or 0) > float(atr.get("atr_mean_20", atr.get("atr_1h", 0)) or 0),
                    "vo_z_cluster_1h": bool(vol.get("vo_z_cluster_1h", False)),
                    "all_conditions_met": (
                        float(ema_slopes.get("ema20_slope", 0) or 0) > 0.0 and
                        float(seps.get("dsep_fast_5", 0) or 0) > 0.0 and
                        float(atr.get("atr_1h", 0) or 0) > float(atr.get("atr_mean_20", atr.get("atr_1h", 0)) or 0) and
                        bool(vol.get("vo_z_cluster_1h", False))
                    ),
                }
            
            features = dict(features)
            features["uptrend_engine"] = payload
            results.append(payload)
        except Exception as e:
            logger.debug(f"Backtest step failed at {bar_ts.isoformat()}: {e}")
            continue

    # Output results
    ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    v2_dir = "backtester/v2"
    os.makedirs(v2_dir, exist_ok=True)
    
    out_json = f"{v2_dir}/backtest_results_v2_{ticker}_{int(end_ts.timestamp())}.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved results to {out_json}")

    chart_file = generate_results_chart(results, contract, chain, sbx)
    if chart_file:
        print(f"Results chart: {chart_file}")
    print(f"Done. Points: {len(results)}")


if __name__ == "__main__":
    main()
