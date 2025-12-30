"""
Regime TA Tracker

Computes technical analysis indicators for regime driver positions.
Reads OHLC from regime_price_data_ohlc and writes features.ta to regime driver positions.

Reference: docs/regime_engine_implementation_plan.md - Phase 2
"""

from __future__ import annotations

import logging
import math
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import Client, create_client  # type: ignore

from src.intelligence.lowcap_portfolio_manager.jobs.ta_utils import (
    atr_series_wilder,
    adx_series_wilder,
    ema_series,
    ema_slope_delta,
    ema_slope_normalized,
    lin_slope,
    rsi,
)

logger = logging.getLogger(__name__)

# Regime drivers
REGIME_DRIVERS = ["BTC", "ALT", "nano", "small", "mid", "big", "BTC.d", "USDT.d"]

# Timeframe mapping: regime TF -> position TF
# Note: Now that schema allows '1d', we can use it directly (no more 4h mapping)
REGIME_TO_POSITION_TF = {
    "1d": "1d",   # Macro regime uses 1d positions
    "1h": "1h",   # Meso regime uses 1h positions
    "1m": "1m",   # Micro regime uses 1m positions
}

# Minimum bars for TA calculation
MIN_BARS = {
    "1m": 333,
    "1h": 72,
    "1d": 30,
}


class RegimeTATracker:
    """
    Computes TA for regime driver positions.
    
    Reads from:
    - regime_price_data_ohlc: OHLC data for drivers
    
    Writes to:
    - lowcap_positions (status=regime_driver): features.ta
    """
    
    def __init__(
        self,
        timeframe: str = "1h",
        book_id: str = "onchain_crypto"
    ) -> None:
        """
        Initialize Regime TA Tracker.
        
        Args:
            timeframe: Regime timeframe ('1m', '1h', '1d')
            book_id: Book ID for asset class scoping
        """
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.timeframe = timeframe
        self.book_id = book_id
        self.ta_suffix = f"_{timeframe}"
        
    def run(self) -> int:
        """
        Run TA computation for all regime drivers.
        
        Returns:
            Number of positions updated
        """
        now = datetime.now(timezone.utc)
        updated = 0
        
        # Bucket drivers that we can check for tokens
        bucket_drivers = ["nano", "small", "mid", "big"]
        
        for driver in REGIME_DRIVERS:
            try:
                # Early skip: Check if bucket has tokens before processing
                if driver in bucket_drivers:
                    if not self._bucket_has_tokens(driver):
                        logger.debug(f"Skipping {driver}/{self.timeframe}: bucket has no tokens")
                        continue
                
                # Get or create regime driver position
                position = self._ensure_regime_position(driver)
                if not position:
                    logger.warning(f"Could not get/create position for {driver}")
                    continue
                
                # Fetch OHLC data
                bars = self._fetch_regime_ohlc(driver)
                min_bars = MIN_BARS.get(self.timeframe, 72)
                
                if len(bars) < min_bars:
                    logger.debug(f"Skipping {driver}/{self.timeframe}: only {len(bars)} bars, need {min_bars}")
                    continue
                
                # Compute TA
                ta = self._compute_ta(bars, now)
                
                # Add latest price for UptrendEngine
                ta["latest_price"] = bars[-1]["c"] if bars else 0.0
                
                # Update position features (per-position read-modify-write)
                self._write_features_ta(position["id"], ta)
                
                updated += 1
                logger.debug(f"Updated TA for {driver}/{self.timeframe}")
                
            except Exception as e:
                logger.error(f"Failed to compute TA for {driver}/{self.timeframe}: {e}")
        
        logger.info(f"Regime TA tracker updated {updated} positions for {self.timeframe}")
        return updated
    
    def _write_features_ta(self, position_id: str, ta: Dict[str, Any]) -> None:
        """Write TA to features using per-position read-modify-write pattern."""
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
            logger.error("Failed to write TA for regime position %s: %s", position_id, e)
            raise

    def _ensure_regime_position(self, driver: str) -> Optional[Dict[str, Any]]:
        """
        Get or create a regime driver position.
        
        Regime driver positions have:
        - status = 'regime_driver'
        - token_ticker = driver name
        - timeframe = regime timeframe
        """
        # Map regime timeframe to position timeframe
        position_tf = REGIME_TO_POSITION_TF.get(self.timeframe, self.timeframe)
        
        # Try to fetch existing position
        result = self.sb.table("lowcap_positions").select("*").eq(
            "token_ticker", driver
        ).eq(
            "timeframe", position_tf
        ).eq(
            "status", "regime_driver"
        ).eq(
            "book_id", self.book_id
        ).limit(1).execute()
        
        if result.data:
            return result.data[0]
        
        # Create new regime driver position
        try:
            new_position = {
                "token_contract": f"regime_{driver.lower().replace('.', '_')}",
                "token_chain": "regime",
                "token_ticker": driver,
                "timeframe": position_tf,
                "status": "regime_driver",
                "state": "S4",  # neutral until EMAs establish a trend
                "book_id": self.book_id,
                "features": {},
            }
            
            result = self.sb.table("lowcap_positions").insert(new_position).execute()
            if result.data:
                logger.info(f"Created regime driver position: {driver}/{position_tf}")
                return result.data[0]
        except Exception as e:
            # Log full error details but don't print to terminal
            logger.error(f"Failed to create regime position {driver}/{position_tf}: {e}", exc_info=True)
        
        return None
    
    def _fetch_regime_ohlc(self, driver: str) -> List[Dict[str, Any]]:
        """Fetch OHLC bars for a regime driver"""
        result = (
            self.sb.table("regime_price_data_ohlc")
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("driver", driver)
            .eq("book_id", self.book_id)
            .eq("timeframe", self.timeframe)
            .order("timestamp", desc=False)
            .limit(400)
            .execute()
        )
        
        bars = []
        for row in result.data or []:
            bars.append({
                "t0": datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00")),
                "o": float(row.get("open_usd") or 0.0),
                "h": float(row.get("high_usd") or 0.0),
                "l": float(row.get("low_usd") or 0.0),
                "c": float(row.get("close_usd") or 0.0),
                "v": float(row.get("volume") or 0.0),
            })
        
        return bars
    
    def _bucket_has_tokens(self, bucket_name: str) -> bool:
        """
        Check if a bucket has any tokens.
        
        Args:
            bucket_name: Bucket name (nano, small, mid, big)
        
        Returns:
            True if bucket has tokens, False otherwise
        """
        try:
            result = (
                self.sb.table("token_cap_bucket")
                .select("token_contract", count="exact")
                .eq("bucket", bucket_name)
                .limit(1)
                .execute()
            )
            # Check if count > 0 (if count is available) or if any rows exist
            if hasattr(result, "count") and result.count is not None:
                return result.count > 0
            # Fallback: check if any data exists
            return len(result.data or []) > 0
        except Exception as e:
            logger.debug(f"Error checking tokens for bucket {bucket_name}: {e}")
            # On error, assume bucket has tokens (let downstream handle empty case)
            return True
    
    def _compute_ta(self, bars: List[Dict[str, Any]], now: datetime) -> Dict[str, Any]:
        """
        Compute TA indicators for bars.
        
        Based on ta_tracker.py but simplified for regime drivers.
        """
        closes = [b["c"] for b in bars]
        
        # EMAs
        ema20 = ema_series(closes, 20)
        ema30 = ema_series(closes, 30)
        ema50 = ema_series(closes, 50)
        ema60 = ema_series(closes, 60)
        ema144 = ema_series(closes, 144)
        ema250 = ema_series(closes, 250)
        ema333 = ema_series(closes, 333)
        
        ema20_val = ema20[-1] if ema20 else closes[-1] if closes else 0.0
        ema30_val = ema30[-1] if ema30 else closes[-1] if closes else 0.0
        ema50_val = ema50[-1] if ema50 else closes[-1] if closes else 0.0
        ema60_val = ema60[-1] if ema60 else closes[-1] if closes else 0.0
        ema144_val = ema144[-1] if ema144 else closes[-1] if closes else 0.0
        ema250_val = ema250[-1] if ema250 else closes[-1] if closes else 0.0
        ema333_val = ema333[-1] if ema333 else closes[-1] if closes else 0.0
        
        # ATR and ADX
        atr_vals = atr_series_wilder(bars, 14)
        adx_vals = adx_series_wilder(bars, 14)
        atr_val = atr_vals[-1] if atr_vals else 0.0
        adx_val = adx_vals[-1] if adx_vals else 0.0
        
        # EMA slopes
        ema20_slope = ema_slope_normalized(ema20, window=10)
        ema60_slope = ema_slope_normalized(ema60, window=10)
        ema144_slope = ema_slope_normalized(ema144, window=10)
        ema250_slope = ema_slope_normalized(ema250, window=10)
        ema333_slope = ema_slope_normalized(ema333, window=10)
        
        # Slope deltas (acceleration)
        d_ema60_slope = ema_slope_delta(ema60, window=10, lag=10)
        d_ema144_slope = ema_slope_delta(ema144, window=10, lag=10)
        d_ema250_slope = ema_slope_delta(ema250, window=10, lag=10)
        d_ema333_slope = ema_slope_delta(ema333, window=10, lag=10)
        
        # Separations
        sep_fast = (ema20_val - ema60_val) / max(ema60_val, 1e-9)
        sep_mid = (ema60_val - ema144_val) / max(ema144_val, 1e-9)
        
        if len(ema60) >= 6 and len(ema144) >= 6 and len(ema20) >= 6:
            sep_fast_prev = (ema20[-6] - ema60[-6]) / max(ema60[-6], 1e-9)
            sep_mid_prev = (ema60[-6] - ema144[-6]) / max(ema144[-6], 1e-9)
        else:
            sep_fast_prev = sep_fast
            sep_mid_prev = sep_mid
        
        dsep_fast_5 = sep_fast - sep_fast_prev
        dsep_mid_5 = sep_mid - sep_mid_prev
        
        # ATR helpers
        atr_norm = atr_val / max(ema50_val, 1e-9)
        atr_mean_20 = statistics.fmean(atr_vals[-20:]) if len(atr_vals) >= 20 else atr_val
        atr_peak_10 = max(atr_vals[-10:]) if len(atr_vals) >= 10 else atr_val
        
        # RSI
        rsi_vals = []
        for k in range(max(15, len(closes) - 60), len(closes)):
            rsi_vals.append(rsi(closes[:k + 1], 14))
        rsi_val = rsi_vals[-1] if rsi_vals else 50.0
        rsi_slope_10 = lin_slope(rsi_vals, 10) if rsi_vals else 0.0
        
        # ADX slope
        adx_slope_10 = lin_slope(adx_vals, 10) if adx_vals else 0.0
        
        # Volume z-score (simplified for regime drivers)
        volumes = [max(0.0, b["v"]) for b in bars]
        if volumes and sum(volumes) > 0:
            log_v = [math.log(1.0 + v) for v in volumes]
            # EWMA for vol z-score
            N = 64
            alpha = 2.0 / (N + 1)
            mu = log_v[0]
            var = 0.0
            for x in log_v[1:]:
                prev_mu = mu
                mu = alpha * x + (1 - alpha) * mu
                var = (1 - alpha) * (var + alpha * (x - prev_mu) * (x - mu))
            sd = math.sqrt(max(var, 1e-12))
            vo_z = (log_v[-1] - mu) / (sd if sd > 0 else 1.0)
            vo_z = max(-4.0, min(6.0, vo_z))
        else:
            vo_z = 0.0
        
        # Build TA dict
        ta = {
            "ema": {
                f"ema20{self.ta_suffix}": ema20_val,
                f"ema30{self.ta_suffix}": ema30_val,
                f"ema50{self.ta_suffix}": ema50_val,
                f"ema60{self.ta_suffix}": ema60_val,
                f"ema144{self.ta_suffix}": ema144_val,
                f"ema250{self.ta_suffix}": ema250_val,
                f"ema333{self.ta_suffix}": ema333_val,
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
                f"atr{self.ta_suffix}": atr_val,
                f"atr_norm{self.ta_suffix}": atr_norm,
                f"atr_mean_20{self.ta_suffix}": atr_mean_20,
                f"atr_peak_10{self.ta_suffix}": atr_peak_10,
            },
            "momentum": {
                f"rsi{self.ta_suffix}": rsi_val,
                f"rsi_slope_10{self.ta_suffix}": rsi_slope_10,
                f"adx{self.ta_suffix}": adx_val,
                f"adx_slope_10{self.ta_suffix}": adx_slope_10,
            },
            "volume": {
                f"vo_z{self.ta_suffix}": vo_z,
            },
            "meta": {
                f"source{self.ta_suffix}": self.timeframe,
                "updated_at": now.isoformat(),
                "bars_count": len(bars),
            },
        }
        
        return ta


def main() -> None:
    """CLI entry point"""
    import argparse
    
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Regime TA Tracker")
    parser.add_argument("--timeframe", type=str, default="1h", help="Timeframe (1m, 1h, 1d)")
    parser.add_argument("--book-id", type=str, default="onchain_crypto", help="Book ID")
    args = parser.parse_args()
    
    tracker = RegimeTATracker(timeframe=args.timeframe, book_id=args.book_id)
    updated = tracker.run()
    print(f"Updated {updated} regime driver positions")


if __name__ == "__main__":
    main()

