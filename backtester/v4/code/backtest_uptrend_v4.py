#!/usr/bin/env python3
"""
Backtest UptrendEngineV4 safely (no production writes).

Key improvements for v4:
- Uses ta_utils.py for all TA calculations (single source of truth)
- Calls engine methods directly (no duplicate logic)
- Preserves all diagnostics in output
- Simplified state machine (no acceleration patterns, no persistence)
"""

from __future__ import annotations

import os
import sys
import json
import logging
import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv  # type: ignore

# Production jobs
from src.intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import GeometryBuilder
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import UptrendEngineV4, Constants
from src.intelligence.lowcap_portfolio_manager.jobs.ta_utils import (
    ema_series,
    lin_slope,
    ema_slope_normalized,
    ema_slope_delta,
    atr_series_wilder,
    adx_series_wilder,
    rsi,
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
        """Fetch OHLC bars up to a timestamp."""
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)  # OHLC table uses "chain", not "token_chain"
            .eq("timeframe", "1h")
            .lte("timestamp", until_iso)
            .order("timestamp", desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return _forward_fill_prices(rows)


def _build_ta_payload_from_rows(rows_1h: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build TA payload from OHLC rows using ta_utils (single source of truth)."""
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

    # Use ta_utils for all EMA calculations
    ema20_1h = ema_series(closes, 20)
    ema30_1h = ema_series(closes, 30)
    ema50_1h = ema_series(closes, 50)
    ema60_1h = ema_series(closes, 60)
    ema144_1h = ema_series(closes, 144)
    ema250_1h = ema_series(closes, 250)
    ema333_1h = ema_series(closes, 333)

    # Use ta_utils for ATR/ADX
    atr_series_1h = atr_series_wilder(bars_1h, 14)
    adx_series_1h = adx_series_wilder(bars_1h, 14)
    adx_1h = adx_series_1h[-1] if adx_series_1h else 0.0

    # VO_z calculation
    v1h = [max(0.0, float(b.get("v") or 0.0)) for b in bars_1h]
    log_v = [math.log(1.0 + v) for v in v1h] if v1h else []
    L = 64
    vo_z_1h = 0.0
    if len(log_v) >= L:
        window = log_v[-L:]
        mean = statistics.fmean(window)
        sd = statistics.pstdev(window) or 1.0
        vo_z_1h = (log_v[-1] - mean) / sd
    vo_z_cluster_1h = bool(vo_z_1h >= 2.0)

    # RSI series
    rsi_series_1h: List[float] = []
    for k in range(max(15, len(closes) - 60), len(closes)):
        rsi_series_1h.append(rsi(closes[: k + 1], 14))
    rsi_1h = rsi_series_1h[-1] if rsi_series_1h else 50.0
    rsi_slope_10 = lin_slope(rsi_series_1h, 10) if rsi_series_1h else 0.0
    adx_slope_10 = lin_slope(adx_series_1h, 10) if adx_series_1h else 0.0

    # Use ta_utils for EMA slopes (normalized %/bar)
    ema20_slope = ema_slope_normalized(ema20_1h, window=10)
    ema30_slope = ema_slope_normalized(ema30_1h, window=10)
    ema60_slope = ema_slope_normalized(ema60_1h, window=10)
    ema144_slope = ema_slope_normalized(ema144_1h, window=10)
    ema250_slope = ema_slope_normalized(ema250_1h, window=10)
    ema333_slope = ema_slope_normalized(ema333_1h, window=10)

    # Slope deltas (acceleration)
    d_ema60_slope = ema_slope_delta(ema60_1h, window=10, lag=10)
    d_ema144_slope = ema_slope_delta(ema144_1h, window=10, lag=10)
    d_ema250_slope = ema_slope_delta(ema250_1h, window=10, lag=10)
    d_ema333_slope = ema_slope_delta(ema333_1h, window=10, lag=10)

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
            "rsi_1h": rsi_1h,
            "rsi_slope_10": rsi_slope_10,
            "adx_1h": adx_1h,
            "adx_slope_10": adx_slope_10,
        },
        "volume": {
            "vo_z_1h": vo_z_1h,
            "vo_z_cluster_1h": vo_z_cluster_1h,
        },
        "ema_slopes": {
            "ema20_slope": ema20_slope,
            "ema30_slope": ema30_slope,
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
            "sep_fast": ((ema20_1h[-1] - ema60_1h[-1]) / max(ema60_1h[-1], 1e-9)) if (ema20_1h and ema60_1h) else 0.0,
            "sep_mid": ((ema60_1h[-1] - ema144_1h[-1]) / max(ema144_1h[-1], 1e-9)) if (ema60_1h and ema144_1h) else 0.0,
            "dsep_fast_5": 0.0,
            "dsep_mid_5": 0.0,
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


class BacktestEngine(UptrendEngineV4):
    """Engine with time-filtered data access for backtesting."""

    def __init__(self, target_ts: datetime):
        super().__init__()
        self.target_ts = target_ts

    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, low_native")
            .eq("token_contract", contract)
            .eq("chain", chain)  # OHLC table uses "chain", not "token_chain"
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

    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 60) -> List[Dict[str, Any]]:
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)  # OHLC table uses "chain", not "token_chain"
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

    def analyze_single(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze one position at target_ts without DB writes - calls engine methods directly."""
        ta = self._read_ta(features)
        if not ta:
            return {"state": "S0", "payload": {}}

        # Get previous payload from features
        prev_payload = dict(features.get("uptrend_engine_v4") or {})
        prev_state = str(prev_payload.get("state") or "")
        
        ema_vals = self._get_ema_values(ta)
        ema_slopes = self._get_ema_slopes(ta)
        last = self._latest_close_1h(contract, chain)
        price = last["close"]
        
        if price <= 0:
            return {"state": "S0", "payload": {}}
        
        sr_levels = self._read_sr_levels(features)
        
        # Call engine's bootstrap logic
        if not prev_state or prev_state == "":
            if self._check_s3_order(ema_vals):
                prev_state = "S3"
            elif self._check_s0_order(ema_vals):
                prev_state = "S0"
            else:
                # No state (S4)
                payload = self._build_payload(
                    "S4",
                    contract,
                    chain,
                    price,
                    ema_vals,
                    features,
                    {"watch_only": True},
                )
                return {"state": "S4", "payload": payload}
        
        # Global exit precedence: fast band at bottom
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
            return {"state": "S0", "payload": payload}
        
        # State machine - call engine methods directly
        payload = None
        
        # S0: Pure Downtrend
        if prev_state == "S0":
            if self._check_fast_band_above_60(ema_vals) and price > ema_vals.get("ema60", 0.0):
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
            else:
                payload = self._build_payload("S0", contract, chain, price, ema_vals, features, {})
        
        # S1: Primer
        elif prev_state == "S1":
            buy_check = self._check_buy_signal_conditions(
                price, ema_vals.get("ema60", 0.0), ema_slopes, ta, sr_levels, anchor_is_333=False
            )
            
            if price > ema_vals.get("ema333", 0.0):
                # S1 → S2
                payload = self._build_payload("S2", contract, chain, price, ema_vals, features, {})
            else:
                # Stay in S1
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
        
        # S2: Defensive Regime
        elif prev_state == "S2":
            if price < ema_vals.get("ema333", 0.0):
                # S2 → S1 (flip-flop back, populate buy_check diagnostics)
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
            elif self._check_s3_order(ema_vals):
                # S2 → S3
                payload = self._build_payload("S3", contract, chain, price, ema_vals, features, {})
            else:
                # Stay in S2
                s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta)
                ox = s3_scores.get("ox", 0.0)
                trim_flag = ox >= Constants.OX_SELL_THRESHOLD
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
        
        # S3: Trending
        elif prev_state == "S3":
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
            else:
                # Stay in S3: Use engine's full S3 logic (includes price <= EMA144 check and EDX sliding scale)
                # Call the engine's run method logic for S3 state
                ta_local = self._read_ta(features)
                s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta_local)
                emergency_exit = price < ema_vals.get("ema333", 0.0)
                ox = s3_scores.get("ox", 0.0)
                dx = s3_scores.get("dx", 0.0)
                edx = s3_scores.get("edx", 0.0)
                
                # Use engine's S3 buy logic (includes price <= EMA144 + slope + TS gates + EDX sliding scale)
                ema144_val = ema_vals.get("ema144", 0.0)
                ema333_val = ema_vals.get("ema333", 0.0)
                price_in_discount_zone = price <= ema144_val if ema144_val > 0 else False
                
                # 1. Slope OK: EMA250_slope > 0.0 OR EMA333_slope >= 0.0 (same as S2 retest)
                ema_slopes = ta_local.get("ema_slopes") or {}
                ema250_slope = float(ema_slopes.get("ema250_slope", 0.0))
                ema333_slope = float(ema_slopes.get("ema333_slope", 0.0))
                slope_ok = (ema250_slope > 0.0) or (ema333_slope >= 0.0)
                
                # 2. TS Gate: TS + S/R boost >= 0.58 (same as S1/S2 entries)
                ts_score = self._compute_ts(ta_local)
                sr_levels = self._read_sr_levels(features)
                atr_val = self._get_atr(ta_local)
                sr_boost = self._compute_sr_boost(price, ema333_val, atr_val, sr_levels)
                ts_with_boost = ts_score + sr_boost
                ts_ok = ts_with_boost >= Constants.TS_THRESHOLD
                
                # EDX suppression
                edx_suppression = 0.0
                if edx >= 0.7:
                    edx_suppression = 0.15
                elif edx >= 0.5:
                    edx_suppression = (edx - 0.5) * 0.5
                dx_threshold_adjusted = Constants.DX_BUY_THRESHOLD + edx_suppression
                
                # Price position boost
                price_position_boost = 0.0
                if price_in_discount_zone and ema333_val > ema144_val and (ema333_val - ema144_val) > 0:
                    band_width = ema333_val - ema144_val
                    price_pos = (price - ema144_val) / band_width
                    price_position_boost = (price_pos * 0.10) - ((1.0 - price_pos) * 0.05)
                dx_threshold_final = max(0.0, dx_threshold_adjusted - price_position_boost)
                
                # Final check: ALL conditions must be met
                dx_ok = dx >= dx_threshold_final
                dx_buy_ok = dx_ok and price_in_discount_zone and slope_ok and ts_ok
                
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
                        "scores": {"ox": ox, "dx": dx, "edx": edx},
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
        
        # Unknown state
        else:
            payload = self._build_payload(prev_state, contract, chain, price, ema_vals, features, {})
        
        return {"state": payload.get("state", "S0"), "payload": payload}


def generate_results_chart(
    results: List[Dict[str, Any]],
    contract: str,
    chain: str,
    sbx: SupabaseCtx,
    ticker: str = "",
) -> str:
    """Generate visualization chart with price, EMAs, states, geometry, and detailed diagnostics.
    
    v4 improvements:
    - Shows TS threshold markers (0.0, 0.3, 0.6, 0.9, 0.58)
    - Shows detailed condition markers for all transitions
    - Includes geometry S/R levels
    - Comprehensive legend with all symbols
    """
    if not results:
        return ""
    
    # Get OHLC data for chart
    end_ts = results[-1].get("ts")
    if not end_ts:
        return ""
    
    rows_all = sbx.fetch_ohlc_1h_lte(contract, chain, end_ts, limit=400)
    if not rows_all:
        return ""
    
    # Build chart data
    chart_times: List[datetime] = []
    chart_closes: List[float] = []
    
    for r in rows_all:
        ts_str = str(r.get("timestamp", ""))
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            close = float(r.get("close_native") or 0.0)
            if close > 0:  # Skip zero prices
                chart_times.append(ts)
                chart_closes.append(close)
        except Exception:
            continue
    
    if not chart_times or not chart_closes:
        return ""
    
    # Trim leading zero prices
    start_idx = 0
    for i, close in enumerate(chart_closes):
        if close > 0:
            start_idx = i
            break
    
    chart_times = chart_times[start_idx:]
    chart_closes = chart_closes[start_idx:]
    
    if not chart_times:
        return ""
    
    # Create figure
    fig, ax = plt.subplots(figsize=(24, 14))
    
    # Build state timeline for vertical bands
    state_timeline: List[Tuple[datetime, datetime, str]] = []  # (start, end, state)
    prev_state = None
    state_start = None
    
    for res in results:
        ts_str = res.get("ts")
        if not ts_str:
            continue
        try:
            res_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if res_ts not in chart_times:
                continue
            
            payload = res.get("payload", {})
            state = payload.get("state", "")
            
            if state != prev_state:
                # End previous state band
                if prev_state and state_start:
                    state_timeline.append((state_start, res_ts, prev_state))
                # Start new state band
                state_start = res_ts
                prev_state = state
        except Exception:
            continue
    
    # Close last state band
    if prev_state and state_start and chart_times:
        state_timeline.append((state_start, chart_times[-1], prev_state))
    
    # Plot price first to establish y-axis range
    ax.plot(chart_times, chart_closes, "k-", linewidth=1.5, label="Price", alpha=0.8, zorder=1)
    
    # Get y-axis range after plotting price
    y_min, y_max = ax.get_ylim()
    
    # Plot vertical state bands (behind everything)
    state_colors = {
        "S0": ("red", 0.15),
        "S1": ("blue", 0.12),
        "S2": ("orange", 0.12),
        "S3": ("green", 0.12),
        "S4": ("gray", 0.1),
    }
    
    for start_ts, end_ts, state in state_timeline:
        color, alpha = state_colors.get(state, ("gray", 0.1))
        ax.axvspan(start_ts, end_ts, ymin=0, ymax=1, color=color, alpha=alpha, zorder=0)
    
    # Build EMA series for plotting
    closes_full = chart_closes
    ema20_chart = ema_series(closes_full, 20)
    ema30_chart = ema_series(closes_full, 30)
    ema60_chart = ema_series(closes_full, 60)
    ema144_chart = ema_series(closes_full, 144)
    ema250_chart = ema_series(closes_full, 250)
    ema333_chart = ema_series(closes_full, 333)
    
    # Plot EMAs
    ax.plot(chart_times, ema20_chart, "b-", linewidth=1, label="EMA20", alpha=0.6, zorder=1)
    ax.plot(chart_times, ema30_chart, "b-", linewidth=1, label="EMA30", alpha=0.6, zorder=1)
    ax.plot(chart_times, ema60_chart, "g-", linewidth=1.5, label="EMA60", alpha=0.7, zorder=1)
    ax.plot(chart_times, ema144_chart, "orange", linewidth=1.5, label="EMA144", alpha=0.7, zorder=1)
    ax.plot(chart_times, ema250_chart, "r-", linewidth=1.5, label="EMA250", alpha=0.7, zorder=1)
    ax.plot(chart_times, ema333_chart, "purple", linewidth=2, label="EMA333", alpha=0.8, zorder=1)
    
    # Get geometry S/R levels
    sr_levels: List[Dict[str, Any]] = []
    seen_prices = set()
    try:
        pos_row = sbx.load_position_features(contract, chain)
        features_geom = dict(pos_row.get("features") or {})
        geometry = features_geom.get("geometry") or {}
        geom_levels = ((geometry.get("levels") or {}).get("sr_levels") or [])
        for geom_lvl in geom_levels[:10]:  # Top 10 S/R levels
            price = float(geom_lvl.get("price", geom_lvl.get("price_native_raw", 0.0)))
            if price > 0 and price not in seen_prices:
                strength = float(geom_lvl.get("strength", 10))
                sr_levels.append({"price": price, "type": "geometry", "strength": strength})
                seen_prices.add(price)
    except Exception as e:
        logger.debug(f"Could not load geometry S/R levels: {e}")
    
    # Plot S/R levels from geometry
    for sr in sr_levels:
        price = sr.get("price", 0.0)
        score = sr.get("strength", 0)
        color = 'blue'
        ax.axhline(y=price, color=color, linestyle='--', alpha=0.4, linewidth=0.8, zorder=2)
        if price > 0 and len(chart_times) > 0:
            ax.text(chart_times[-1], price, f' S/R:{int(score)}', verticalalignment='center', 
                   fontsize=7, color=color, alpha=0.6)
    
    # Collect state transitions and condition markers
    prev_state = None
    state_transitions: List[Tuple[datetime, float, str, str]] = []
    
    # Condition markers
    s0_to_s1: List[Tuple[datetime, float]] = []
    s1_to_s2: List[Tuple[datetime, float]] = []
    s2_to_s3: List[Tuple[datetime, float]] = []
    s1_to_s0: List[Tuple[datetime, float]] = []
    s2_to_s1: List[Tuple[datetime, float]] = []
    s2_to_s0: List[Tuple[datetime, float]] = []
    s3_to_s0: List[Tuple[datetime, float]] = []
    
    buy_signals: List[Tuple[datetime, float, str]] = []  # (time, price, state)
    trim_flags: List[Tuple[datetime, float]] = []
    
    ts_threshold_0: List[Tuple[datetime, float]] = []
    ts_threshold_0_3: List[Tuple[datetime, float]] = []
    ts_threshold_0_6: List[Tuple[datetime, float]] = []
    ts_threshold_0_9: List[Tuple[datetime, float]] = []
    ts_threshold_buy: List[Tuple[datetime, float]] = []
    
    # Collect EDX values for S3 states (for secondary axis plotting)
    edx_times: List[datetime] = []
    edx_values: List[float] = []
    
    # Process results
    for res in results:
        ts_str = res.get("ts")
        if not ts_str:
            continue
        
        try:
            res_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if res_ts not in chart_times:
                continue
            
            payload = res.get("payload", {})
            state = payload.get("state", "")
            price = float(payload.get("price", 0.0))
            
            # Track state transitions
            if prev_state is not None and state != prev_state:
                state_transitions.append((res_ts, price, prev_state, state))
            
            prev_state = state
            
            # Buy signals with state context (redundant state markers removed - using vertical bands instead)
            if payload.get("buy_signal"):  # S1 buy
                buy_signals.append((res_ts, price, "S1"))
            elif payload.get("buy_flag") and state == "S2":  # S2 retest buy
                buy_signals.append((res_ts, price, "S2"))
            elif payload.get("buy_flag") and state == "S3":  # S3 DX buy
                buy_signals.append((res_ts, price, "S3"))
            
            # Trim flags
            if payload.get("trim_flag"):
                trim_flags.append((res_ts, price))
            
            # TS threshold markers (from diagnostics)
            diagnostics = payload.get("diagnostics", {})
            buy_check = diagnostics.get("buy_check", {})
            if buy_check:
                ts_with_boost = buy_check.get("ts_with_boost", 0.0)
                entry_zone_ok = buy_check.get("entry_zone_ok", False)
                slope_ok = buy_check.get("slope_ok", False)
                
                # Show TS threshold markers if entry_zone and slope are OK
                if entry_zone_ok and slope_ok:
                    if ts_with_boost >= 0.9:
                        ts_threshold_0_9.append((res_ts, price))
                    elif ts_with_boost >= 0.6:
                        ts_threshold_0_6.append((res_ts, price))
                    elif ts_with_boost >= 0.3:
                        ts_threshold_0_3.append((res_ts, price))
                    elif ts_with_boost >= 0.0:
                        ts_threshold_0.append((res_ts, price))
                    
                    # Actual buy signal marker (>= 0.58)
                    if ts_with_boost >= Constants.TS_THRESHOLD:
                        ts_threshold_buy.append((res_ts, price))
            
            # Collect EDX for S3 states (for secondary axis)
            if state == "S3":
                scores = payload.get("scores", {})
                edx_val = scores.get("edx", 0.0)
                edx_times.append(res_ts)
                edx_values.append(edx_val)
        
        except Exception:
            continue
    
    # Plot state transitions
    transition_colors = {
        ('S0', 'S1'): 'green',
        ('S1', 'S2'): 'blue',
        ('S2', 'S3'): 'orange',
        ('S1', 'S0'): 'red',
        ('S2', 'S1'): 'gray',
        ('S2', 'S0'): 'red',
        ('S3', 'S0'): 'darkred',
    }
    transition_markers = {
        ('S0', 'S1'): 'o',
        ('S1', 'S2'): 's',
        ('S2', 'S3'): 'D',
        ('S1', 'S0'): 'X',
        ('S2', 'S1'): 's',
        ('S2', 'S0'): 'X',
        ('S3', 'S0'): 'X',
    }
    
    labeled_transitions = set()
    for ts, price, from_state, to_state in state_transitions:
        key = (from_state, to_state)
        color = transition_colors.get(key, 'gray')
        marker = transition_markers.get(key, 'o')
        label = f'{from_state}→{to_state}' if key not in labeled_transitions else ''
        if key not in labeled_transitions:
            labeled_transitions.add(key)
            # Update condition lists for legend
            if key == ('S0', 'S1'):
                s0_to_s1.append((ts, price))
            elif key == ('S1', 'S2'):
                s1_to_s2.append((ts, price))
            elif key == ('S2', 'S3'):
                s2_to_s3.append((ts, price))
            elif key == ('S1', 'S0'):
                s1_to_s0.append((ts, price))
            elif key == ('S2', 'S1'):
                s2_to_s1.append((ts, price))
            elif key == ('S2', 'S0'):
                s2_to_s0.append((ts, price))
            elif key == ('S3', 'S0'):
                s3_to_s0.append((ts, price))
        
        ax.scatter(ts, price, color=color, s=300, marker=marker, 
                   edgecolors='black', linewidths=2, alpha=0.9, 
                   label=label, zorder=12)
    
    # Plot buy signals with colored outlines by state
    if buy_signals:
        s1_buys = [(t, p) for t, p, s in buy_signals if s == "S1"]
        s2_buys = [(t, p) for t, p, s in buy_signals if s == "S2"]
        s3_buys = [(t, p) for t, p, s in buy_signals if s == "S3"]
        
        if s1_buys:
            times, prices_vals = zip(*s1_buys)
            ax.scatter(times, prices_vals, c="lime", marker="D", s=250, alpha=0.9, 
                       zorder=8, edgecolors="blue", linewidths=3, label=f"S1 BUY ({len(s1_buys)})")
        if s2_buys:
            times, prices_vals = zip(*s2_buys)
            ax.scatter(times, prices_vals, c="lime", marker="D", s=250, alpha=0.9, 
                       zorder=8, edgecolors="orange", linewidths=3, label=f"S2 Retest BUY ({len(s2_buys)})")
        if s3_buys:
            times, prices_vals = zip(*s3_buys)
            ax.scatter(times, prices_vals, c="lime", marker="D", s=250, alpha=0.9, 
                       zorder=8, edgecolors="purple", linewidths=3, label=f"S3 DX BUY ({len(s3_buys)})")
    
    # Plot trim flags
    if trim_flags:
        times, prices_vals = zip(*trim_flags)
        ax.scatter(times, prices_vals, c="yellow", marker="x", s=200, alpha=0.9, 
                   zorder=7, linewidths=3, label=f"Trim Flag ({len(trim_flags)})")
    
    # Plot TS threshold markers
    if ts_threshold_0:
        times, prices_vals = zip(*ts_threshold_0)
        ax.scatter(times, prices_vals, c="lightgreen", marker=".", s=30, alpha=0.4, 
                   zorder=4, label=f"TS+boost>=0.0 ({len(ts_threshold_0)})")
    if ts_threshold_0_3:
        times, prices_vals = zip(*ts_threshold_0_3)
        ax.scatter(times, prices_vals, c="yellowgreen", marker=".", s=40, alpha=0.5, 
                   zorder=4, label=f"TS+boost>=0.3 ({len(ts_threshold_0_3)})")
    if ts_threshold_0_6:
        times, prices_vals = zip(*ts_threshold_0_6)
        ax.scatter(times, prices_vals, c="green", marker=".", s=50, alpha=0.5, 
                   zorder=4, label=f"TS+boost>=0.6 ({len(ts_threshold_0_6)})")
    if ts_threshold_0_9:
        times, prices_vals = zip(*ts_threshold_0_9)
        ax.scatter(times, prices_vals, c="darkgreen", marker=".", s=60, alpha=0.6, 
                   zorder=4, label=f"TS+boost>=0.9 ({len(ts_threshold_0_9)})")
    if ts_threshold_buy:
        times, prices_vals = zip(*ts_threshold_buy)
        ax.scatter(times, prices_vals, c="darkgreen", marker="P", s=180, alpha=0.8, 
                   zorder=6, edgecolors="black", linewidths=1, label=f"TS+boost>=0.58 BUY ({len(ts_threshold_buy)})")
    
    # Create secondary y-axis for EDX (S3 only)
    ax2 = None
    if edx_times and edx_values:
        ax2 = ax.twinx()
        ax2.plot(edx_times, edx_values, color="darkred", linewidth=2, linestyle="--", 
                alpha=0.7, label="EDX (S3)", zorder=5)
        ax2.set_ylabel("EDX (0-1)", fontsize=10, color="darkred")
        ax2.set_ylim(0, 1)
        ax2.tick_params(axis='y', labelcolor="darkred", labelsize=9)
    
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Price", fontsize=12)
    title = f"Uptrend Engine v4 Backtest"
    if ticker:
        title += f" - {ticker}"
    ax.set_title(title, fontsize=16, fontweight="bold")
    
    # Comprehensive legend organized by category
    handles, labels = ax.get_legend_handles_labels()
    
    # Get handles/labels from secondary axis if it exists
    if ax2:
        handles2, labels2 = ax2.get_legend_handles_labels()
        handles.extend(handles2)
        labels.extend(labels2)
    
    # Reorganize legend: Price/EMAs, States, Transitions, Signals, TS Thresholds, EDX
    legend_handles = []
    legend_labels = []
    
    # Price and EMAs
    for i, label in enumerate(labels):
        if label in ["Price", "EMA20", "EMA30", "EMA60", "EMA144", "EMA250", "EMA333"]:
            legend_handles.append(handles[i])
            legend_labels.append(label)
    
    legend_handles.append(plt.Line2D([0], [0], color='blue', linestyle='--', alpha=0.4, linewidth=0.8))
    legend_labels.append("Geometry S/R Levels")
    
    # State markers
    legend_handles.append(plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='red', markersize=8, alpha=0.5))
    legend_labels.append("S0 State")
    legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=8, alpha=0.5))
    legend_labels.append("S1 State")
    legend_handles.append(plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='orange', markersize=8, alpha=0.5))
    legend_labels.append("S2 State")
    legend_handles.append(plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='green', markersize=10, alpha=0.6))
    legend_labels.append("S3 State")
    
    # State transitions
    for handle, label in zip(handles, labels):
        if '→' in label:
            legend_handles.append(handle)
            legend_labels.append(label)
    
    # Signals
    for handle, label in zip(handles, labels):
        if "BUY Signal" in label or "Trim Flag" in label:
            legend_handles.append(handle)
            legend_labels.append(label)
    
    # TS thresholds
    for handle, label in zip(handles, labels):
        if "TS+boost" in label:
            legend_handles.append(handle)
            legend_labels.append(label)
    
    # EDX (from secondary axis)
    for handle, label in zip(handles, labels):
        if "EDX" in label:
            legend_handles.append(handle)
            legend_labels.append(label)
    
    ax.legend(legend_handles, legend_labels, loc="upper left", fontsize=9, ncol=2, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save chart
    output_dir = os.path.join(project_root, "backtester", "v4", "backests")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = int(_now_utc().timestamp())
    filename = f"backtest_results_v4_{ticker}_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    
    return filepath


def analyze_single(
    contract: str,
    chain: str,
    target_ts: datetime,
    sbx: SupabaseCtx,
) -> Dict[str, Any]:
    """Analyze one position at a specific timestamp."""
    # Load position features
    pos = sbx.load_position_features(contract, chain)
    features = pos.get("features") or {}
    
    # Build TA from OHLC up to target_ts
    rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, target_ts.isoformat(), limit=400)
    ta = _build_ta_payload_from_rows(rows_1h)
    
    if not ta:
        return {"ts": target_ts.isoformat(), "state": "S0", "payload": {}}
    
    # Merge TA into features
    features["ta"] = ta
    
    # Run geometry once (if not already done)
    if "geometry" not in features or not features.get("geometry"):
        try:
            geom_builder = GeometryBuilder(generate_charts=False)
            geom_builder.build()
            # Reload to get geometry
            pos = sbx.load_position_features(contract, chain)
            features = pos.get("features") or {}
            features["ta"] = ta
        except Exception as e:
            logger.debug("Geometry build skipped: %s", e)
    
    # Analyze with engine
    engine = BacktestEngine(target_ts)
    result = engine.analyze_single(contract, chain, features)
    
    payload = result.get("payload", {})
    payload["ts"] = target_ts.isoformat()
    
    return {
        "ts": target_ts.isoformat(),
        "state": result.get("state", "S0"),
        "payload": payload,
    }


def main() -> None:
    """Main backtest entry point."""
    # Get inputs
    if len(sys.argv) >= 2:
        ticker = sys.argv[1].upper()
        days = int(sys.argv[2]) if len(sys.argv) >= 3 else 14
    else:
        print("Usage: python3 backtest_uptrend_v4.py <TOKEN_TICKER> [days]")
        print("\nExample: python3 backtest_uptrend_v4.py DREAMS 14")
        return
    
    sbx = SupabaseCtx()
    
    # Look up token
    pos_res = (
        sbx.sb.table("lowcap_positions")
        .select("token_contract, token_chain, token_ticker")
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
    ticker = pos_res.data[0].get("token_ticker", ticker)
    
    print(f"Found {ticker}: {contract[:20]}... on {chain}")
    print(f"Running backtest for {days} days...")
    
    # Get end timestamp (last available bar)
    last_row = (
        sbx.sb.table("lowcap_price_data_ohlc")
        .select("timestamp")
        .eq("token_contract", contract)
        .eq("chain", chain)  # OHLC table uses "chain", not "token_chain"
        .eq("timeframe", "1h")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
        .data
    )
    
    if not last_row:
        print("No OHLC data found")
        return
    
    end_ts = datetime.fromisoformat(str(last_row[0]["timestamp"]).replace("Z", "+00:00"))
    start_ts = end_ts - timedelta(days=days)
    
    # Run backtest hour by hour
    results: List[Dict[str, Any]] = []
    current_ts = start_ts
    
    # Load initial position features
    pos = sbx.load_position_features(contract, chain)
    features = pos.get("features") or {}
    
    print(f"Analyzing from {start_ts.isoformat()} to {end_ts.isoformat()}...")
    
    while current_ts <= end_ts:
        try:
            # Build TA for current timestamp
            rows_1h = sbx.fetch_ohlc_1h_lte(contract, chain, current_ts.isoformat(), limit=400)
            ta = _build_ta_payload_from_rows(rows_1h)
            
            if ta:
                features["ta"] = ta
            
            # Analyze with engine (uses prev state from features)
            engine = BacktestEngine(current_ts)
            result = engine.analyze_single(contract, chain, features)
            
            payload = result.get("payload", {})
            payload["ts"] = current_ts.isoformat()
            
            results.append({
                "ts": current_ts.isoformat(),
                "state": result.get("state", "S0"),
                "payload": payload,
            })
            
            # Update features for next iteration (simulate state persistence)
            if payload:
                features["uptrend_engine_v4"] = payload
            
        except Exception as e:
            logger.debug("Error at %s: %s", current_ts.isoformat(), e)
        
        current_ts += timedelta(hours=1)
        
        if len(results) % 24 == 0:
            print(f"  Processed {len(results)} hours...")
    
    print(f"✅ Analyzed {len(results)} hours")
    
    # Save results JSON
    output_dir = os.path.join(project_root, "backtester", "v4", "backests")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = int(end_ts.timestamp())
    json_filename = f"backtest_results_v4_{ticker}_{timestamp}.json"
    json_filepath = os.path.join(output_dir, json_filename)
    
    with open(json_filepath, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"✅ Saved results to {json_filename}")
    
    # Generate chart
    chart_path = generate_results_chart(results, contract, chain, sbx, ticker)
    if chart_path:
        print(f"✅ Generated chart: {os.path.basename(chart_path)}")
    else:
        print("⚠️  Chart generation failed")
    
    print(f"\n{'='*60}")
    print(f"Backtest complete! Check: {output_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

