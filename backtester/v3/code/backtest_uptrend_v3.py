#!/usr/bin/env python3
"""
Backtest UptrendEngineV3 safely (no production writes).
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
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v3 import UptrendEngineV3, Constants
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

    def slope(series: List[float], win: int, normalize: bool = False, latest_val: float = 0.0) -> float:
        """Calculate linear regression slope. If normalize=True, returns %/bar (divides by latest_val)."""
        vals = [v for v in series if v is not None]
        raw_slope = _lin_slope(vals, win) if vals else 0.0
        if normalize and latest_val > 0:
            return raw_slope / max(latest_val, 1e-9)
        return raw_slope

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
            "ema20_slope": slope(ema20_1h, 10, normalize=True, latest_val=ema20_1h[-1] if ema20_1h else 0.0),
            "ema30_slope": slope(ema30_1h, 10, normalize=True, latest_val=ema30_1h[-1] if ema30_1h else 0.0),
            "ema60_slope": slope(ema60_1h, 10, normalize=True, latest_val=ema60_1h[-1] if ema60_1h else 0.0),
            "ema144_slope": slope(ema144_1h, 10, normalize=True, latest_val=ema144_1h[-1] if ema144_1h else 0.0),
            "ema250_slope": slope(ema250_1h, 10, normalize=True, latest_val=ema250_1h[-1] if ema250_1h else 0.0),
            "ema333_slope": slope(ema333_1h, 10, normalize=True, latest_val=ema333_1h[-1] if ema333_1h else 0.0),
            "d_ema60_slope": slope(ema60_1h, 5, normalize=True, latest_val=ema60_1h[-1] if ema60_1h else 0.0) - slope(ema60_1h, 10, normalize=True, latest_val=ema60_1h[-1] if ema60_1h else 0.0),
            "d_ema144_slope": slope(ema144_1h, 5, normalize=True, latest_val=ema144_1h[-1] if ema144_1h else 0.0) - slope(ema144_1h, 10, normalize=True, latest_val=ema144_1h[-1] if ema144_1h else 0.0),
            "d_ema250_slope": slope(ema250_1h, 5, normalize=True, latest_val=ema250_1h[-1] if ema250_1h else 0.0) - slope(ema250_1h, 10, normalize=True, latest_val=ema250_1h[-1] if ema250_1h else 0.0),
            "d_ema333_slope": slope(ema333_1h, 5, normalize=True, latest_val=ema333_1h[-1] if ema333_1h else 0.0) - slope(ema333_1h, 10, normalize=True, latest_val=ema333_1h[-1] if ema333_1h else 0.0),
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


class BacktestEngine(UptrendEngineV3):
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

    def analyze_single(self, contract: str, chain: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze one position at target_ts without DB writes - uses v3's run() logic."""
        ta = self._read_ta(features)
        if not ta:
            return {"state": "S0", "payload": {}}

        # Get previous payload from features
        prev_payload = dict(features.get("uptrend_engine_v3") or {})
        prev_state = str(prev_payload.get("state") or "")
        
        ema_vals = self._get_ema_values(ta)
        last = self._latest_close_1h(contract, chain)
        price = last["close"]
        
        if price <= 0:
            return {"state": "S0", "payload": {}}
        
        # Use v3's state machine logic - manually simulate the run() method for single position
        payload = None
        
        # Bootstrap: If no previous state, determine initial state
        if not prev_state or prev_state == "":
            if self._check_s3_order(ema_vals):
                # Bootstrap to S3
                s3_scores = self._compute_s3_scores(contract, chain, features)
                ti_ts = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                payload = self._build_payload("S3", features, {
                    "flags": {
                        "trending": True,
                        "dx_flag": s3_scores["flags"]["dx_flag"],
                        "emergency_exit": {"active": False},
                    },
                    "scores": {
                        **s3_scores["scores"],
                        "ti": ti_ts["trend_integrity"],
                        "ts": ti_ts["trend_strength"],
                    },
                    "diagnostics": s3_scores["diagnostics"],
                })
                
                # Add geometry context for S3 exits
                try:
                    ta_local = self._read_ta(features)
                    atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                    last_px = price
                    halo = max(0.5 * atr_1h, 0.03 * last_px) if last_px > 0 else 0.0
                    
                    sr_levels = self._read_sr_levels(features)
                    flipped_sr = []
                    for sr in sr_levels[:5]:
                        try:
                            sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                            if sr_price > 0:
                                flipped_sr.append({
                                    "level": sr_price,
                                    "score": float(sr.get("strength", 10) or 10)
                                })
                        except Exception:
                            pass
                    
                    flipped_sr.sort(key=lambda x: float(x.get("level", 0.0)), reverse=True)
                    base_sr = float(flipped_sr[-1].get("level", 0.0)) if flipped_sr else 0.0
                    
                    payload["sr_context"] = {
                        "halo": halo,
                        "base_sr_level": base_sr,
                        "flipped_sr_levels": flipped_sr,
                    }
                except Exception:
                    payload["sr_context"] = {}
                
                features = s3_scores["features"]
            else:
                # Bootstrap to S0
                payload = self._build_payload("S0", features, {
                    "flag": {"watch_only": True},
                    "scores": {},
                })
        
        # S0: Perfect bearish order
        if not payload and self._check_s0_order(ema_vals):
            payload = self._build_payload("S0", features, {
                "flag": {"watch_only": True},
                "scores": {},
            })
            # Clear any S1/S2 meta when in S0
            meta = dict(features.get("uptrend_engine_v3_meta") or {})
            meta.pop("s1", None)
            meta.pop("s2", None)
            features["uptrend_engine_v3_meta"] = meta
        
        # Global precedence: fast band at bottom → exit to S0
        if not payload and self._check_fast_band_at_bottom(ema_vals):
            payload = self._build_payload("S0", features, {
                "flag": {"watch_only": True},
                "scores": {},
                "diagnostics": {"s1_exit": True, "reason": "fast_band_at_bottom"},
            })
        
        # S1: Simplified - Fast band above 60 + Price above 60, must come from S0
        if not payload and self._check_fast_band_above_60(ema_vals) and price > ema_vals["ema60"]:
            if prev_state == "S0" or not prev_state:
                payload = self._build_payload("S1", features, {
                    "flag": {"s1_valid": True},
                    "scores": {},
                })
            elif prev_state == "S1":
                payload = self._build_payload("S1", features, {
                    "flag": {"s1_valid": True},
                    "scores": {},
                })
        
        # Enter S2: price > EMA333 from S1
        if not payload and prev_state == "S1" and price > ema_vals["ema333"]:
            payload = self._build_payload("S2", features, {
                "flag": {"defensive": True},
                "scores": {},
            })
        
        # BUY SIGNAL: From S1 (no S2 state)
        if not payload and prev_state == "S1":
            buy_check = self._check_buy_signal_conditions(contract, chain, features, ema_vals, price)
            if buy_check["entry_ready"]:
                meta = dict(features.get("uptrend_engine_v3_meta") or {})
                s1_meta = dict(meta.get("s1") or {})
                if "ema60_entry" not in s1_meta:
                    s1_meta["ema60_entry"] = ema_vals["ema60"]
                    meta["s1"] = s1_meta
                    features["uptrend_engine_v3_meta"] = meta
                payload = self._build_payload("S1", features, {
                    "flag": {
                        "s1_valid": True,
                        "buy_signal": True,
                        "entry_zone": buy_check["entry_zone"],
                    },
                    "scores": {
                        "ts": buy_check["ts_score"],
                        "ts_with_boost": buy_check.get("ts_with_boost", buy_check["ts_score"]),
                    },
                    "levels": {
                        "base_sr_level": s1_meta.get("ema60_entry", ema_vals["ema60"]),
                    },
                })
            else:
                payload = self._build_payload("S1", features, {
                    "flag": {"s1_valid": True},
                    "scores": {
                        "ts": buy_check.get("ts_score", 0.0),
                        "ts_with_boost": buy_check.get("ts_with_boost", buy_check.get("ts_score", 0.0)),
                    },
                })
        
        # S2 management (defensive)
        if not payload and prev_state == "S2":
            if price < ema_vals["ema333"]:
                payload = self._build_payload("S1", features, {
                    "flag": {"s1_valid": True},
                    "scores": {},
                    "diagnostics": {"s2_to_s1": True, "reason": "price_below_ema333"},
                })
            else:
                s3_scores = self._compute_s3_scores(contract, chain, features)
                ox = float(s3_scores["scores"].get("ox", 0.0))
                trim_flag = ox >= Constants.OX_SELL_THRESHOLD
                ta_local = self._read_ta(features)
                atr = ta_local.get("atr") or {}
                atr_1h = float(atr.get("atr_1h") or 0.0)
                entry_zone_333 = False
                if ema_vals["ema333"] > 0 and atr_1h > 0:
                    entry_zone_333 = abs(price - ema_vals["ema333"]) <= (1.0 * atr_1h)
                slopes = (ta_local.get("ema_slopes") or {})
                ema250_slope = float(slopes.get("ema250_slope") or 0.0)
                ema333_slope = float(slopes.get("ema333_slope") or 0.0)
                slope_ok_333 = (ema250_slope > 0.0) or (ema333_slope >= 0.0)
                ts_block = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                ts_base = float(ts_block.get("trend_strength") or 0.0)
                ts_with_boost = ts_base
                sr_levels = self._read_sr_levels(features)
                if sr_levels and ema_vals["ema333"] > 0 and atr_1h > 0:
                    halo = 1.0 * atr_1h
                    for sr in sr_levels[:10]:
                        try:
                            sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                            if sr_price > 0 and abs(sr_price - ema_vals["ema333"]) <= halo:
                                sr_strength = float(sr.get("strength", 10) or 10)
                                boost = min(0.15, (sr_strength / 20.0) * 0.15)
                                ts_with_boost = min(1.0, ts_base + boost)
                                break
                        except Exception:
                            pass
                buy_flag = entry_zone_333 and slope_ok_333 and (ts_with_boost >= Constants.TS_ENTRY_THRESHOLD)
                payload = self._build_payload("S2", features, {
                    "flag": {
                        "defensive": True,
                        "trim_flag": trim_flag,
                        "buy_flag": buy_flag,
                        "entry_zone_333": entry_zone_333,
                    },
                    "scores": {
                        "ox": ox,
                        "ts": ts_base,
                        "ts_with_boost": ts_with_boost,
                    },
                })
        
        # S2 → S3: full bullish alignment (band-based)
        if not payload and prev_state == "S2" and self._check_bullish_alignment_band(ema_vals):
            payload = self._build_payload("S3", features, {
                "flags": {"trending": True},
                "scores": {},
                "diagnostics": {"s2_to_s3": True, "reason": "bullish_alignment_band"},
            })
        
        # S2 stay/management
        elif not payload and prev_state == "S2":
            meta = dict(features.get("uptrend_engine_v3_meta") or {})
            s2_meta = dict(meta.get("s2") or {})
            ema60_entry = float(s2_meta.get("ema60_entry") or ema_vals["ema60"])
            
            # Check for S2→S0 reset (fast band below 60, with 3-bar persistence)
            fast_band_below = not self._check_fast_band_above_60(ema_vals)
            if fast_band_below:
                reset_count = int(s2_meta.get("reset_persistence", 0)) + 1
                s2_meta["reset_persistence"] = reset_count
                meta["s2"] = s2_meta
                features["uptrend_engine_v3_meta"] = meta
                
                if reset_count >= Constants.S2_RESET_PERSISTENCE_BARS:
                    # Reset to S0 after persistence
                    meta.pop("s1", None)
                    meta.pop("s2", None)
                    features["uptrend_engine_v3_meta"] = meta
                    payload = self._build_payload("S0", features, {
                        "flag": {"watch_only": True},
                        "scores": {},
                        "diagnostics": {"s2_reset": True, "reason": "fast_band_below_60"},
                    })
                else:
                    # Still in S2, but reset building (emit S2 with warning)
                    payload = self._build_payload("S2", features, {
                        "flag": {
                            "uptrend_holding": True,
                            "reset_pending": True,
                        },
                        "scores": {},
                        "levels": {
                            "base_sr_level": ema60_entry,
                        },
                    })
            else:
                # Fast band still above 60, clear reset counter
                s2_meta["reset_persistence"] = 0
                meta["s2"] = s2_meta
                features["uptrend_engine_v3_meta"] = meta
                
                # Stay in S2
                # Check entry zone (within halo = 0.5 * ATR of EMA60)
                ta_local = self._read_ta(features)
                atr = ta_local.get("atr") or {}
                atr_1h = float(atr.get("atr_1h") or 0.0)
                in_entry_zone = False
                if ema60_entry > 0 and atr_1h > 0:
                    halo = 0.5 * atr_1h
                    in_entry_zone = abs(price - ema60_entry) <= halo
                
                ti_ts = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                
                payload = self._build_payload("S2", features, {
                    "flag": {
                        "uptrend_holding": in_entry_zone,
                    },
                    "scores": {
                        "ti": ti_ts["trend_integrity"],
                        "ts": ti_ts["trend_strength"],
                    },
                    "levels": {
                        "base_sr_level": ema60_entry,
                    },
                })
        
        # S3: All EMAs above 333 - ONLY from S2!
        elif not payload and prev_state == "S2" and self._check_s3_order(ema_vals):
            # Check for S3→S0 reset FIRST (all EMAs break below 333)
            all_emas_below_333 = (
                ema_vals["ema20"] < ema_vals["ema333"] and
                ema_vals["ema30"] < ema_vals["ema333"] and
                ema_vals["ema60"] < ema_vals["ema333"] and
                ema_vals["ema144"] < ema_vals["ema333"] and
                ema_vals["ema250"] < ema_vals["ema333"]
            )
            
            if all_emas_below_333:
                # Reset to S0
                meta = dict(features.get("uptrend_engine_v3_meta") or {})
                meta.pop("s1", None)
                meta.pop("s2", None)
                features["uptrend_engine_v3_meta"] = meta
                payload = self._build_payload("S0", features, {
                    "flag": {"watch_only": True},
                    "scores": {},
                    "diagnostics": {"s3_reset": True, "reason": "all_emas_below_333"},
                })
            else:
                # Stay in S3
                s3_scores = self._compute_s3_scores(contract, chain, features)
                ti_ts = self._compute_ti_ts_s2(contract, chain, features, ema_vals)
                
                # Check emergency exit
                em_exit = self._check_emergency_exit(contract, chain, features, ema_vals, price, prev_payload)
                
                payload = self._build_payload("S3", features, {
                    "flags": {
                        "trending": True,
                        "dx_flag": s3_scores["flags"]["dx_flag"],
                        "emergency_exit": em_exit,
                    },
                    "scores": {
                        **s3_scores["scores"],
                        "ti": ti_ts["trend_integrity"],
                        "ts": ti_ts["trend_strength"],
                    },
                    "diagnostics": s3_scores["diagnostics"],
                })
                
                # Add geometry context for S3 exits (kept for exits per spec)
                try:
                    ta_local = self._read_ta(features)
                    atr_1h = float((ta_local.get("atr") or {}).get("atr_1h") or 0.0)
                    last_px = price
                    halo = max(0.5 * atr_1h, 0.03 * last_px) if last_px > 0 else 0.0
                    
                    # Get S/R levels from geometry (for exit decisions)
                    sr_levels = self._read_sr_levels(features)
                    flipped_sr = []
                    for sr in sr_levels[:5]:  # Top 5 S/R levels
                        try:
                            sr_price = float(sr.get("price", sr.get("price_rounded_native", 0.0)))
                            if sr_price > 0:
                                flipped_sr.append({
                                    "level": sr_price,
                                    "score": float(sr.get("strength", 10) or 10)
                                })
                        except Exception:
                            pass
                    
                    flipped_sr.sort(key=lambda x: float(x.get("level", 0.0)), reverse=True)
                    base_sr = float(flipped_sr[-1].get("level", 0.0)) if flipped_sr else 0.0
                    
                    payload["sr_context"] = {
                        "halo": halo,
                        "base_sr_level": base_sr,
                        "flipped_sr_levels": flipped_sr,
                    }
                except Exception:
                    payload["sr_context"] = {}
                
                features = s3_scores["features"]
                
                # Check fakeout recovery (if emergency exit was active and price recovered)
                prev_em_active = bool(prev_payload.get("flags", {}).get("emergency_exit", {}).get("active") or False)
                if prev_em_active and price > ema_vals["ema333"]:
                    if ti_ts["trend_integrity"] >= Constants.TI_ENTRY_THRESHOLD and ti_ts["trend_strength"] >= Constants.TS_ENTRY_THRESHOLD:
                        # Fakeout recovery
                        payload["flags"]["fakeout_recovery"] = True
                        payload["flags"]["emergency_exit"] = {"active": False}
                        meta = dict(features.get("uptrend_engine_v3_meta") or {})
                        meta.pop("emergency_exit", None)
                        features["uptrend_engine_v3_meta"] = meta
        
        # Default fallback to S0
        if not payload:
            payload = self._build_payload("S0", features, {
                "flag": {"watch_only": True},
                "scores": {},
            })
        
        return {"state": payload.get("state", "S0"), "payload": payload}


def generate_results_chart(results: List[Dict[str, Any]], contract: str, chain: str, sbx: SupabaseCtx) -> str:
    """Generate visualization chart with price, EMAs, states, and detailed condition markers."""
    if not results:
        return ""
    
    timestamps: List[datetime] = []
    prices: List[float] = []
    states: List[str] = []
    
    # Signal markers
    dx_buy_signals: List[Tuple[datetime, float, float]] = []
    dx_near_miss: List[Tuple[datetime, float, float]] = []
    ox_sell_signals: List[Tuple[datetime, float, float]] = []
    
    # BUY signals (from S1, no S2 state)
    buy_signals: List[Tuple[datetime, float, float]] = []  # (time, price, ts_with_boost)
    
    # TS threshold markers (entries that would trigger at different TS+boost levels)
    ts_threshold_0: List[Tuple[datetime, float]] = []  # TS+boost >= 0.0
    ts_threshold_0_3: List[Tuple[datetime, float]] = []  # TS+boost >= 0.3
    ts_threshold_0_6: List[Tuple[datetime, float]] = []  # TS+boost >= 0.6
    ts_threshold_0_9: List[Tuple[datetime, float]] = []  # TS+boost >= 0.9
    
    # S0→S1 condition markers
    s0_to_s1_fast_band: List[Tuple[datetime, float]] = []  # Fast band above 60
    s0_to_s1_accel_a: List[Tuple[datetime, float]] = []  # S1.A Accelerating up
    s0_to_s1_accel_b: List[Tuple[datetime, float]] = []  # S1.B Steady lift
    s1_valid: List[Tuple[datetime, float]] = []  # S1 valid (all conditions met)
    s1_cancel: List[Tuple[datetime, float]] = []  # S1 cancel conditions
    
    # S1→S2 condition markers
    s1_to_s2_price_above_60: List[Tuple[datetime, float]] = []
    s1_to_s2_entry_zone: List[Tuple[datetime, float]] = []
    s1_to_s2_slope_ok: List[Tuple[datetime, float]] = []
    s1_to_s2_ti_ok: List[Tuple[datetime, float]] = []
    s1_to_s2_ts_ok: List[Tuple[datetime, float]] = []
    s1_to_s2_blocked: List[Tuple[datetime, float]] = []  # Blocked by cancel persistence
    
    # S2→S3 condition markers
    s2_to_s3_all_above_333: List[Tuple[datetime, float]] = []
    
    # S2→S0 reset markers
    s2_reset_fast_band_below: List[Tuple[datetime, float, int]] = []  # (time, price, persistence_count)
    
    # S1→S0 exit markers (fast band at bottom)
    s1_exit: List[Tuple[datetime, float]] = []
    
    # S2→S1 exit markers (price below EMA333)
    s2_to_s1: List[Tuple[datetime, float]] = []
    
    # S3 condition markers
    s3_emergency_exit: List[Tuple[datetime, float]] = []
    s3_fakeout_recovery: List[Tuple[datetime, float]] = []
    s3_reset_all_below_333: List[Tuple[datetime, float]] = []
    
    # Thresholds (Normal aggressiveness: A=0.5)
    A = 0.5
    tau_dx = 0.80 - 0.30 * A  # 0.65
    tau_trim = 0.8 - 0.3 * A  # 0.65
    
    for r in results:
        ts = r.get("analysis_ts")
        if not ts:
            continue
        ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        timestamps.append(ts_dt)
        price = float(((r.get('levels') or {}).get('current_price')) or 0.0)
        prices.append(price)
        state = str(r.get("state") or "S0")
        states.append(state)
        
        payload = r.get("payload") or {}
        scores = payload.get("scores") or {}
        flags = payload.get("flags") or payload.get("flag") or {}
        diagnostics = payload.get("diagnostics") or {}
        acceleration = payload.get("acceleration") or {}
        
        # Extract acceleration info
        ema60_accel = acceleration.get("ema60") or {}
        accel_type = str(ema60_accel.get("type", ""))
        
        dx = float(scores.get("dx", 0.0))
        ox = float(scores.get("ox", 0.0))
        edx = float(scores.get("edx", 0.0))
        dx_flag = bool(flags.get("dx_flag", False))
        ti_score = float(scores.get("ti", 0.0))
        ts_score = float(scores.get("ts", 0.0))
        
        # S0→S1 condition tracking
        if state == "S1":
            s1_valid_flag = bool(flags.get("s1_valid", False))
            in_cancel_persistence = bool(flags.get("in_cancel_persistence", False))
            
            if accel_type == "accelerating_up":
                s0_to_s1_accel_a.append((ts_dt, price))
            elif accel_type == "steady_lift":
                s0_to_s1_accel_b.append((ts_dt, price))
            
            if s1_valid_flag:
                s1_valid.append((ts_dt, price))
                # Fast band above 60 confirmed
                if not in_cancel_persistence:
                    s0_to_s1_fast_band.append((ts_dt, price))
            
            if in_cancel_persistence:
                s1_cancel.append((ts_dt, price))
        
        # S1→S2 condition tracking (check when in S1 OR S2)
        s2_entry_check = diagnostics.get("s2_entry_check") or {}
        
        # When in S1: show what's blocking the transition
        if state == "S1" and s2_entry_check:
            # Track each condition individually
            if bool(s2_entry_check.get("price_above_60", False)):
                s1_to_s2_price_above_60.append((ts_dt, price))
            else:
                # Show missing condition
                pass  # Will add "missing" markers below
            
            if bool(s2_entry_check.get("fast_above_60", False)):
                pass  # Already covered by fast band check
            else:
                pass  # Missing condition
            
            if bool(s2_entry_check.get("entry_zone", False)):
                s1_to_s2_entry_zone.append((ts_dt, price))
            
            if bool(s2_entry_check.get("slope_ok", False)):
                s1_to_s2_slope_ok.append((ts_dt, price))
            
            if bool(s2_entry_check.get("ti_ok", False)):
                s1_to_s2_ti_ok.append((ts_dt, price))
            
            if bool(s2_entry_check.get("ts_ok", False)):
                s1_to_s2_ts_ok.append((ts_dt, price))
            
            # Track what's MISSING (blocking the transition)
            entry_ready = bool(s2_entry_check.get("entry_ready", False))
            if not entry_ready:
                # Show why it's blocked
                if not s2_entry_check.get("price_above_60", True):
                    s1_to_s2_blocked.append((ts_dt, price))  # Blocked: price not above 60
                elif not s2_entry_check.get("entry_zone", True):
                    s1_to_s2_blocked.append((ts_dt, price))  # Blocked: not in entry zone
                elif not s2_entry_check.get("slope_ok", True):
                    s1_to_s2_blocked.append((ts_dt, price))  # Blocked: slope not OK
                elif not s2_entry_check.get("ti_ok", True):
                    s1_to_s2_blocked.append((ts_dt, price))  # Blocked: TI too low
                elif not s2_entry_check.get("ts_ok", True):
                    s1_to_s2_blocked.append((ts_dt, price))  # Blocked: TS too low
        
        # BUY signals and TS threshold tracking (all S1 states, not just when buy_signal is true)
        if state == "S1":
            # Check buy signal conditions (entry_zone + slope_ok) - these are stored in diagnostics
            # We need to recompute them here for TS threshold markers
            # Actually, we can get this from the buy_check diagnostics if available
            # But for now, let's check if we have buy_check info
            buy_check_info = diagnostics.get("buy_check") or {}
            entry_zone_ok = buy_check_info.get("entry_zone", False)
            slope_ok = buy_check_info.get("slope_ok", False)
            
            # Get TS with boost (or base TS if no boost)
            ts_with_boost = float(scores.get("ts_with_boost", scores.get("ts", ts_score)))
            
            # Only show TS threshold markers when ALL buy conditions are met (entry_zone + slope_ok)
            # This makes the markers meaningful - they show potential entries at different TS levels
            if entry_zone_ok and slope_ok:
                if ts_with_boost >= 0.0:
                    ts_threshold_0.append((ts_dt, price))
                if ts_with_boost >= 0.3:
                    ts_threshold_0_3.append((ts_dt, price))
                if ts_with_boost >= 0.6:
                    ts_threshold_0_6.append((ts_dt, price))
                if ts_with_boost >= 0.9:
                    ts_threshold_0_9.append((ts_dt, price))
            
            # Actual buy signals (TS+boost >= 0.58 threshold and buy_signal flag true)
            buy_signal = bool(flags.get("buy_signal", False))
            if buy_signal:
                buy_signals.append((ts_dt, price, ts_with_boost))
        
        # Also check for cancel persistence blocking
        if state == "S1":
            in_cancel_block = bool(flags.get("in_cancel_persistence", False))
            if in_cancel_block:
                s1_to_s2_blocked.append((ts_dt, price))
        
        # S1→S0 exit tracking (fast band at bottom)
        s1_exit_info = diagnostics.get("s1_exit")
        if s1_exit_info:
            s1_exit.append((ts_dt, price))
        
        # S2→S1 exit tracking (price below EMA333)
        s2_to_s1_info = diagnostics.get("s2_to_s1")
        if s2_to_s1_info:
            s2_to_s1.append((ts_dt, price))
        
        # S2→S0 reset tracking
        s2_reset_info = diagnostics.get("s2_reset")
        if s2_reset_info:
            # Try to get reset persistence from features (stored in previous iteration)
            # For now, just mark that reset condition was detected
            s2_reset_fast_band_below.append((ts_dt, price, 1))  # Simplified - just mark occurrence
        
        # S2→S3 condition tracking
        if state == "S3" and states and len(states) > 1 and states[-2] == "S2":
            s2_to_s3_all_above_333.append((ts_dt, price))
        
        # S3 condition tracking
        if state == "S3":
            em_exit = flags.get("emergency_exit") or {}
            if bool(em_exit.get("active", False)):
                s3_emergency_exit.append((ts_dt, price))
            
            if bool(flags.get("fakeout_recovery", False)):
                s3_fakeout_recovery.append((ts_dt, price))
            
            s3_reset_info = diagnostics.get("s3_reset")
            if s3_reset_info:
                s3_reset_all_below_333.append((ts_dt, price))
        
        # DX buy signals
        if dx_flag:
            if dx >= tau_dx:
                dx_buy_signals.append((ts_dt, price, dx))
            else:
                dx_near_miss.append((ts_dt, price, dx))
        
        # OX sell signals
        edx_boost = max(0.0, min(0.5, edx - 0.5))
        ox_adj = ox * (1.0 + 0.33 * edx_boost)
        if ox_adj >= tau_trim:
            ox_sell_signals.append((ts_dt, price, ox_adj))
    
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
    # Trim leading zeros: skip until first valid close > 0
    first_valid_idx = None
    for i, b in enumerate(bars_1h):
        if b["c"] > 0:
            first_valid_idx = i
            break
    if first_valid_idx is not None and first_valid_idx > 0:
        bars_1h = bars_1h[first_valid_idx:]
    closes = [b["c"] for b in bars_1h]
    bar_times = [b["t0"] for b in bars_1h]
    
    # Calculate EMAs
    ema20_1h = _ema_series(closes, 20)
    ema30_1h = _ema_series(closes, 30)
    ema60_1h = _ema_series(closes, 60)
    ema144_1h = _ema_series(closes, 144)
    ema250_1h = _ema_series(closes, 250)
    ema333_1h = _ema_series(closes, 333)
    
    # Get S/R levels from geometry
    sr_levels: List[Dict[str, Any]] = []
    seen_prices = set()
    
    try:
        if results:
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
    
    # Add S/R levels from results
    try:
        for r in results:
            payload = r.get("payload") or {}
            sr_context = payload.get("sr_context") or {}
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
            
            levels = payload.get("levels") or {}
            base_sr = levels.get("base_sr_level")
            if base_sr:
                price = float(base_sr)
                if price > 0 and price not in seen_prices:
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
    
    # Find and plot state transitions
    prev_state = None
    state_transitions = []
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
    
    # Plot state transition markers
    transition_colors = {
        ('S0', 'S1'): 'green',
        ('S1', 'S2'): 'blue',
        ('S2', 'S3'): 'orange',
        ('S3', 'S0'): 'red',
        ('S2', 'S0'): 'red',
        ('S1', 'S0'): 'gray',
        ('S2', 'S1'): 'gray',
    }
    transition_markers = {
        ('S0', 'S1'): 'o',
        ('S1', 'S2'): 's',
        ('S2', 'S3'): 'D',
        ('S3', 'S0'): 'X',
        ('S2', 'S0'): 'X',
        ('S1', 'S0'): 'o',  # Grey circle
        ('S2', 'S1'): 's',   # Grey square
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
    
    # Find ATL
    all_result_prices = [float(((r.get('levels') or {}).get('current_price')) or 0.0) for r in results if (r.get('levels') or {}).get('current_price')]
    if all_result_prices:
        atl_price = min(all_result_prices)
        ax1.axhline(y=atl_price, color='red', linestyle=':', linewidth=2, alpha=0.8, label='ATL')
        if len(bar_times) > 0:
            ax1.text(bar_times[-1], atl_price, f' ATL', verticalalignment='center', 
                    fontsize=9, color='red', alpha=0.9, weight='bold')
    
    # Plot S/R levels (geometry only, skip EMA60 base)
    for sr in sr_levels:
        price = sr.get("price", 0.0)
        sr_type = sr.get("type", "unknown")
        score = sr.get("strength", 0)
        if sr_type == 'ema60_s2' or sr_type == 'base':
            continue
        color = 'blue'
        ax1.axhline(y=price, color=color, linestyle='--', alpha=0.6, linewidth=1)
        if price > 0 and len(bar_times) > 0:
            ax1.text(bar_times[-1], price, f' {score}', verticalalignment='center', 
                    fontsize=8, color=color, alpha=0.8)
    
    # Plot S0→S1 condition markers
    if s0_to_s1_fast_band:
        times, prices_vals = zip(*s0_to_s1_fast_band)
        ax1.scatter(times, prices_vals, color='cyan', s=60, marker='.', alpha=0.6, 
                   label=f'S0→S1: Fast band >60 ({len(s0_to_s1_fast_band)})', zorder=6)
    
    if s0_to_s1_accel_a:
        times, prices_vals = zip(*s0_to_s1_accel_a)
        ax1.scatter(times, prices_vals, color='blue', s=80, marker='s', alpha=0.7, 
                   edgecolors='darkblue', linewidths=1, label=f'S1.A: Accelerating ({len(s0_to_s1_accel_a)})', zorder=6)
    
    if s0_to_s1_accel_b:
        times, prices_vals = zip(*s0_to_s1_accel_b)
        ax1.scatter(times, prices_vals, color='lightblue', s=80, marker='s', alpha=0.7, 
                   edgecolors='blue', linewidths=1, label=f'S1.B: Steady lift ({len(s0_to_s1_accel_b)})', zorder=6)
    
    # Replace "S1 Valid" with more specific markers - don't plot generic "valid"
    # Instead show: Fast band above 60, Acceleration type, etc. (already done above)
    
    if s1_cancel:
        times, prices_vals = zip(*s1_cancel)
        ax1.scatter(times, prices_vals, color='red', s=100, marker='x', alpha=0.8, 
                   edgecolors='darkred', linewidths=2, label=f'S1 Cancel ({len(s1_cancel)})', zorder=7)
    
    # Plot S1→S2 condition markers
    if s1_to_s2_price_above_60:
        times, prices_vals = zip(*s1_to_s2_price_above_60)
        ax1.scatter(times, prices_vals, color='lime', s=70, marker='.', alpha=0.6, 
                   label=f'S1→S2: Price >60 ({len(s1_to_s2_price_above_60)})', zorder=5)
    
    if s1_to_s2_entry_zone:
        times, prices_vals = zip(*s1_to_s2_entry_zone)
        ax1.scatter(times, prices_vals, color='greenyellow', s=90, marker='.', alpha=0.7, 
                   label=f'S1→S2: Entry zone ({len(s1_to_s2_entry_zone)})', zorder=5)
    
    if s1_to_s2_slope_ok:
        times, prices_vals = zip(*s1_to_s2_slope_ok)
        ax1.scatter(times, prices_vals, color='teal', s=70, marker='^', alpha=0.6, 
                   label=f'S1→S2: Slope OK ({len(s1_to_s2_slope_ok)})', zorder=5)
    
    if s1_to_s2_ti_ok:
        times, prices_vals = zip(*s1_to_s2_ti_ok)
        ax1.scatter(times, prices_vals, color='magenta', s=70, marker='.', alpha=0.6, 
                   label=f'S1→S2: TI≥0.45 ({len(s1_to_s2_ti_ok)})', zorder=5)
    
    if s1_to_s2_ts_ok:
        times, prices_vals = zip(*s1_to_s2_ts_ok)
        ax1.scatter(times, prices_vals, color='purple', s=70, marker='.', alpha=0.6, 
                   label=f'S1→S2: TS≥0.58 ({len(s1_to_s2_ts_ok)})', zorder=5)
    
    # S1→S2 blocked conditions - show detailed reasons
    if s1_to_s2_blocked:
        times, prices_vals = zip(*s1_to_s2_blocked)
        ax1.scatter(times, prices_vals, color='darkred', s=150, marker='X', alpha=1.0, 
                   edgecolors='red', linewidths=3, label=f'S1→S2: BLOCKED ({len(s1_to_s2_blocked)})', zorder=13)
    
    # Missing conditions when in S1 (show why S1→S2 isn't happening)
    s1_missing_price: List[Tuple[datetime, float]] = []
    s1_missing_entry_zone: List[Tuple[datetime, float]] = []
    s1_missing_slope: List[Tuple[datetime, float]] = []
    s1_missing_ti: List[Tuple[datetime, float]] = []
    s1_missing_ts: List[Tuple[datetime, float]] = []
    
    # Re-scan results to find missing conditions when in S1
    for r in results:
        ts = r.get("analysis_ts")
        if not ts:
            continue
        ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        price = float(((r.get('levels') or {}).get('current_price')) or 0.0)
        state = str(r.get("state") or "S0")
        
        if state == "S1":
            payload = r.get("payload") or {}
            diagnostics = payload.get("diagnostics") or {}
            s2_entry_check = diagnostics.get("s2_entry_check") or {}
            
            if s2_entry_check:
                # Track what's missing
                if not s2_entry_check.get("price_above_60", True):
                    s1_missing_price.append((ts_dt, price))
                if s2_entry_check.get("price_above_60", False) and not s2_entry_check.get("entry_zone", True):
                    s1_missing_entry_zone.append((ts_dt, price))
                if s2_entry_check.get("entry_zone", False) and not s2_entry_check.get("slope_ok", True):
                    s1_missing_slope.append((ts_dt, price))
                if s2_entry_check.get("slope_ok", False) and not s2_entry_check.get("ti_ok", True):
                    s1_missing_ti.append((ts_dt, price))
                if s2_entry_check.get("ti_ok", False) and not s2_entry_check.get("ts_ok", True):
                    s1_missing_ts.append((ts_dt, price))
    
    # Plot missing conditions
    if s1_missing_price:
        times, prices_vals = zip(*s1_missing_price)
        ax1.scatter(times, prices_vals, color='orange', s=100, marker='v', alpha=0.7, 
                   edgecolors='darkorange', linewidths=2, label=f'S1: Missing Price>60 ({len(s1_missing_price)})', zorder=4)
    
    if s1_missing_entry_zone:
        times, prices_vals = zip(*s1_missing_entry_zone)
        ax1.scatter(times, prices_vals, color='orange', s=100, marker='<', alpha=0.7, 
                   edgecolors='darkorange', linewidths=2, label=f'S1: Missing Entry Zone ({len(s1_missing_entry_zone)})', zorder=4)
    
    if s1_missing_slope:
        times, prices_vals = zip(*s1_missing_slope)
        ax1.scatter(times, prices_vals, color='orange', s=100, marker='>', alpha=0.7, 
                   edgecolors='darkorange', linewidths=2, label=f'S1: Missing Slope ({len(s1_missing_slope)})', zorder=4)
    
    if s1_missing_ti:
        times, prices_vals = zip(*s1_missing_ti)
        ax1.scatter(times, prices_vals, color='pink', s=100, marker='.', alpha=0.7, 
                   edgecolors='magenta', linewidths=1, label=f'S1: Missing TI≥0.45 ({len(s1_missing_ti)})', zorder=4)
    
    if s1_missing_ts:
        times, prices_vals = zip(*s1_missing_ts)
        ax1.scatter(times, prices_vals, color='pink', s=100, marker='.', alpha=0.7, 
                   edgecolors='purple', linewidths=1, label=f'S1: Missing TS≥0.58 ({len(s1_missing_ts)})', zorder=4)
    
    # Plot S2→S3 condition markers
    if s2_to_s3_all_above_333:
        times, prices_vals = zip(*s2_to_s3_all_above_333)
        ax1.scatter(times, prices_vals, color='gold', s=150, marker='D', alpha=0.9, 
                   edgecolors='orange', linewidths=2, label=f'S2→S3: All >333 ({len(s2_to_s3_all_above_333)})', zorder=10)
    
    # Plot S2→S0 reset markers
    if s2_reset_fast_band_below:
        times, prices_vals, persist_counts = zip(*s2_reset_fast_band_below)
        ax1.scatter(times, prices_vals, color='crimson', s=100, marker='x', alpha=0.8, 
                   edgecolors='darkred', linewidths=2, label=f'S2→S0: Reset ({len(s2_reset_fast_band_below)})', zorder=9)
    
    # Plot S1→S0 exit markers (grey circle)
    if s1_exit:
        times, prices_vals = zip(*s1_exit)
        ax1.scatter(times, prices_vals, color='gray', s=200, marker='o', alpha=0.9, 
                   edgecolors='black', linewidths=2, label=f'S1→S0 ({len(s1_exit)})', zorder=12)
    
    # Plot S2→S1 exit markers (grey square)
    if s2_to_s1:
        times, prices_vals = zip(*s2_to_s1)
        ax1.scatter(times, prices_vals, color='gray', s=200, marker='s', alpha=0.9, 
                   edgecolors='black', linewidths=2, label=f'S2→S1 ({len(s2_to_s1)})', zorder=12)
    
    # Plot S3 condition markers
    if s3_emergency_exit:
        times, prices_vals = zip(*s3_emergency_exit)
        ax1.scatter(times, prices_vals, color='red', s=150, marker='v', alpha=0.9, 
                   edgecolors='darkred', linewidths=2, label=f'S3: Emergency exit ({len(s3_emergency_exit)})', zorder=11)
    
    if s3_fakeout_recovery:
        times, prices_vals = zip(*s3_fakeout_recovery)
        ax1.scatter(times, prices_vals, color='lime', s=150, marker='^', alpha=0.9, 
                   edgecolors='darkgreen', linewidths=2, label=f'S3: Fakeout recovery ({len(s3_fakeout_recovery)})', zorder=11)
    
    if s3_reset_all_below_333:
        times, prices_vals = zip(*s3_reset_all_below_333)
        ax1.scatter(times, prices_vals, color='darkred', s=150, marker='X', alpha=0.9, 
                   edgecolors='red', linewidths=2, label=f'S3→S0: Reset ({len(s3_reset_all_below_333)})', zorder=11)
    
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
    
    # BUY signals at different TS+boost thresholds
    if ts_threshold_0:
        times, prices_vals = zip(*ts_threshold_0)
        ax1.scatter(times, prices_vals, color='lightblue', s=100, marker='o', alpha=0.5, 
                   edgecolors='blue', linewidths=1, label=f'TS+boost >= 0.0 ({len(ts_threshold_0)})', zorder=7)
    
    if ts_threshold_0_3:
        times, prices_vals = zip(*ts_threshold_0_3)
        ax1.scatter(times, prices_vals, color='cyan', s=120, marker='s', alpha=0.6, 
                   edgecolors='darkcyan', linewidths=1.5, label=f'TS+boost >= 0.3 ({len(ts_threshold_0_3)})', zorder=8)
    
    if ts_threshold_0_6:
        times, prices_vals = zip(*ts_threshold_0_6)
        ax1.scatter(times, prices_vals, color='green', s=140, marker='^', alpha=0.7, 
                   edgecolors='darkgreen', linewidths=2, label=f'TS+boost >= 0.6 ({len(ts_threshold_0_6)})', zorder=9)
    
    if ts_threshold_0_9:
        times, prices_vals = zip(*ts_threshold_0_9)
        ax1.scatter(times, prices_vals, color='lime', s=160, marker='*', alpha=0.9, 
                   edgecolors='darkgreen', linewidths=2.5, label=f'TS+boost >= 0.9 ({len(ts_threshold_0_9)})', zorder=10)
    
    # Actual buy signals (TS+boost >= 0.58 threshold)
    if buy_signals:
        buy_times, buy_prices, buy_ts = zip(*buy_signals)
        ax1.scatter(buy_times, buy_prices, color='yellow', s=180, marker='*', alpha=1.0, 
                   edgecolors='orange', linewidths=3, label=f'BUY Signal (TS+boost >= 0.58: {len(buy_signals)})', zorder=11)
    
    ax1.grid(True, alpha=0.3)
    
    # Get ticker for title
    ticker = "UNKNOWN"
    try:
        pos_row = sbx.load_position_features(contract, chain)
        ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    except Exception:
        pass
    
    ax1.set_title(f'{ticker} Backtest V3 - Detailed Condition Analysis', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price (Native)', fontsize=12)
    
    # Create a much larger legend with better organization
    # Split legend into multiple columns and place it outside the plot
    handles, labels = ax1.get_legend_handles_labels()
    
    # Organize legend into sections
    state_transition_labels = []
    condition_labels = []
    signal_labels = []
    
    state_transition_handles = []
    condition_handles = []
    signal_handles = []
    
    # Categorize items
    for handle, label in zip(handles, labels):
        if '→' in label or 'Reset' in label or 'Valid' in label or 'Cancel' in label:
            state_transition_handles.append(handle)
            state_transition_labels.append(label)
        elif 'OX' in label or 'DX' in label or 'Buy' in label or 'Sell' in label:
            signal_handles.append(handle)
            signal_labels.append(label)
        else:
            condition_handles.append(handle)
            condition_labels.append(label)
    
    # Create custom legend with sections
    fig.legend(state_transition_handles + condition_handles + signal_handles,
               state_transition_labels + condition_labels + signal_labels,
               loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=8, 
               ncol=1, framealpha=0.9, fancybox=True, shadow=True)
    
    # Adjust layout to make room for legend
    plt.tight_layout(rect=[0, 0, 0.75, 1])
    
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
    v3_dir = "backtester/v3/backests"
    os.makedirs(v3_dir, exist_ok=True)
    out = f"{v3_dir}/backtest_results_{ticker}_{int(_now_utc().timestamp())}.png"
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
            print("Usage: python3 backtest_uptrend_v3.py <TOKEN_TICKER> [days]")
            print("   or: Set BT_CONTRACT, BT_CHAIN, BT_DAYS env vars")
            print("\nExample: python3 backtest_uptrend_v3.py DREAMS 14")
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

    print(f"\n=== Starting Backtest V3 ===")
    print(f"Token: {contract[:20]}... on {chain}")
    print(f"Period: {days} days")
    print(f"From: {start_ts.isoformat()}")
    print(f"To: {end_ts.isoformat()}\n")

    # Step 1: Ensure geometry present (needed for S3 exits)
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
            result = engine.analyze_single(contract, chain, features)
            
            payload = result.get("payload") or {}
            last_close = float(rows_1h_filled[-1].get("close_native") or 0.0) if rows_1h_filled else 0.0
            if last_close <= 0:
                continue
            
            payload.setdefault("levels", {})["current_price"] = last_close
            payload["analysis_ts"] = bar_ts.isoformat()
            payload["contract"] = contract
            payload["chain"] = chain
            payload["state"] = result.get("state", "S0")
            
            features = dict(features)
            features["uptrend_engine_v3"] = payload
            results.append({
                "state": result.get("state", "S0"),
                "payload": payload,
                "analysis_ts": bar_ts.isoformat(),
                "contract": contract,
                "chain": chain,
                "levels": payload.get("levels", {}),
            })
        except Exception as e:
            logger.debug(f"Backtest step failed at {bar_ts.isoformat()}: {e}")
            continue

    # Output results
    ticker = pos_row.get("token_ticker", contract[:8]) or contract[:8]
    v3_dir = "backtester/v3/backests"
    os.makedirs(v3_dir, exist_ok=True)
    
    out_json = f"{v3_dir}/backtest_results_v3_{ticker}_{int(end_ts.timestamp())}.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Saved results to {out_json}")

    chart_file = generate_results_chart(results, contract, chain, sbx)
    if chart_file:
        print(f"Results chart: {chart_file}")
    print(f"Done. Points: {len(results)}")


if __name__ == "__main__":
    main()

