"""
Regime Price Collector

Collects and computes OHLC data for regime drivers:
- BTC: Direct from Binance API (backfill) + majors table (live)
- ALT: Composite of SOL, ETH, BNB (avg opens/closes, max highs, min lows, sum volumes)
- Buckets (nano, small, mid, big): Composite from lowcap positions
- BTC.d, USDT.d: Dominance from CoinGecko (percentage treated as price)

Reference: docs/regime_engine_implementation_plan.md - Phase 1
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from supabase import Client, create_client  # type: ignore

logger = logging.getLogger(__name__)

# Configuration
BINANCE_BASE_URL = "https://api.binance.com"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Regime drivers
MAJOR_SYMBOLS = {
    "BTC": "BTCUSDT",
    "SOL": "SOLUSDT",
    "ETH": "ETHUSDT",
    "BNB": "BNBUSDT",
}
ALT_COMPONENTS = ["SOL", "ETH", "BNB", "HYPE"]  # Components for ALT composite
# Note: HYPE is not available on Binance, so it can only be backfilled from Hyperliquid WS
# If HYPE data is missing, ALT composite will use SOL/ETH/BNB only
MAJORS = ["BTC", "SOL", "ETH", "BNB", "HYPE"]  # Symbols that go to majors_price_data_ohlc
REGIME_DRIVERS = ["BTC"]  # Symbols that go to regime_price_data_ohlc

# Market cap bucket thresholds (USD)
BUCKET_THRESHOLDS = {
    "nano": (0, 10_000_000),           # < $10M
    "small": (10_000_000, 50_000_000), # $10M - $50M
    "mid": (50_000_000, 200_000_000),  # $50M - $200M
    "big": (200_000_000, float("inf")), # > $200M
}

# Timeframe configurations
REGIME_TIMEFRAMES = ["1m", "1h", "1d"]
BINANCE_INTERVALS = {"1m": "1m", "1h": "1h", "1d": "1d"}

# Rate limiting
RATE_LIMIT_DELAY = 0.1  # 100ms between API calls


@dataclass
class OHLCBar:
    """Standard OHLC bar"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open_usd": self.open,
            "high_usd": self.high,
            "low_usd": self.low,
            "close_usd": self.close,
            "volume": self.volume,
        }


class RegimePriceCollector:
    """
    Collects and computes OHLC data for all regime drivers.
    
    Drivers:
    - BTC: Bitcoin price (from Binance/majors)
    - ALT: Composite of SOL, ETH, BNB
    - nano, small, mid, big: Market cap bucket composites
    - BTC.d, USDT.d: Dominance percentages (treated as price)
    """
    
    def __init__(self, book_id: str = "onchain_crypto") -> None:
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        self.book_id = book_id
        
    # =========================================================================
    # Public API
    # =========================================================================
    
    def run(self, timeframe: str = "1h") -> Dict[str, Any]:
        """
        Main entry point - collect all regime driver data for a timeframe.
        
        Args:
            timeframe: '1m', '1h', or '1d'
            
        Returns:
            Summary of collection results
        """
        logger.info(f"Running regime price collection for {timeframe}")
        results = {
            "timeframe": timeframe,
            "drivers_collected": [],
            "errors": [],
        }
        
        # 1. Collect majors (BTC and ALT components)
        try:
            self._collect_majors(timeframe)
            results["drivers_collected"].append("BTC")
            results["drivers_collected"].append("ALT")
        except Exception as e:
            logger.error(f"Failed to collect majors: {e}")
            results["errors"].append(f"majors: {e}")
        
        # 2. Collect bucket composites
        try:
            self._collect_bucket_composites(timeframe)
            results["drivers_collected"].extend(["nano", "small", "mid", "big"])
        except Exception as e:
            logger.error(f"Failed to collect buckets: {e}")
            results["errors"].append(f"buckets: {e}")
        
        # 3. Collect dominance (only for 1m - rollup to others)
        if timeframe == "1m":
            try:
                self._collect_dominance()
                results["drivers_collected"].extend(["BTC.d", "USDT.d"])
            except Exception as e:
                logger.error(f"Failed to collect dominance: {e}")
                results["errors"].append(f"dominance: {e}")
        
        logger.info(f"Regime collection complete: {len(results['drivers_collected'])} drivers")
        return results
    
    def backfill_majors_from_hyperliquid(
        self, 
        days: int = 90,
        timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Backfill historical majors data from Hyperliquid candleSnapshot API.
        
        Uses Hyperliquid's candleSnapshot endpoint for more accurate historical data
        (same venue as trading). Falls back to Binance only if Hyperliquid fails.
        
        Args:
            days: Number of days to backfill
            timeframes: List of timeframes to backfill (default: all regime TFs)
            
        Returns:
            Summary of backfill results
        """
        if timeframes is None:
            timeframes = REGIME_TIMEFRAMES
            
        logger.info(f"Backfilling {days} days of majors from Hyperliquid")
        results = {
            "days": days,
            "symbols": [],
            "bars_written": 0,
            "errors": [],
        }
        
        # Map Hyperliquid intervals (regime timeframes use same names)
        interval_map = {"1m": "1m", "1h": "1h", "1d": "1d"}
        
        # Backfill majors: BTC, SOL, ETH, BNB, HYPE
        # Use uppercase symbols to match Hyperliquid naming convention
        for symbol_key in ["BTC", "SOL", "ETH", "BNB", "HYPE"]:
            if symbol_key not in ALT_COMPONENTS and symbol_key != "BTC":
                continue  # Skip if not in ALT components (HYPE is included)
                
            for tf in timeframes:
                try:
                    interval = interval_map.get(tf, tf)
                    if not interval:
                        logger.warning(f"Skipping {symbol_key}/{tf}: unsupported interval")
                        continue
                    
                    # Backfill from Hyperliquid
                    from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_backfill import backfill_from_hyperliquid
                    candles_written = backfill_from_hyperliquid(
                        self.sb,
                        coin=symbol_key,
                        interval=interval,
                        days=days
                    )
                    
                    if candles_written == 0:
                        logger.warning(f"No candles backfilled for {symbol_key}/{tf} from Hyperliquid, trying Binance fallback")
                        # Fallback to Binance for non-BTC symbols (if available)
                        if symbol_key != "BTC" and symbol_key in MAJOR_SYMBOLS:
                            binance_symbol = MAJOR_SYMBOLS[symbol_key]
                            bars = self._fetch_binance_klines(binance_symbol, tf, days)
                            self._write_majors_ohlc(symbol_key, tf, bars)
                            candles_written = len(bars)
                            logger.info(f"Backfilled {len(bars)} {symbol_key} bars from Binance fallback for {tf}")
                    else:
                        # Transform Hyperliquid candles to appropriate tables
                        # Read from hyperliquid_price_data_ohlc and write to majors/regime
                        self._sync_hyperliquid_to_majors_regime(symbol_key, tf, days)
                        results["bars_written"] += candles_written
                        logger.info(f"Backfilled {candles_written} {symbol_key} bars from Hyperliquid for {tf}")
                        
                except Exception as e:
                    logger.error(f"Failed to backfill {symbol_key}/{tf}: {e}", exc_info=True)
                    results["errors"].append(f"{symbol_key}/{tf}: {e}")
                    
            results["symbols"].append(symbol_key)
        
        # Compute ALT composite from backfilled data
        for tf in timeframes:
            try:
                self._compute_alt_composite(tf, days)
            except Exception as e:
                logger.error(f"Failed to compute ALT composite for {tf}: {e}")
                results["errors"].append(f"ALT/{tf}: {e}")
        
        logger.info(f"Backfill complete: {results['bars_written']} bars written")
        return results
    
    def _sync_hyperliquid_to_majors_regime(self, symbol: str, timeframe: str, days: int) -> None:
        """
        Sync candles from hyperliquid_price_data_ohlc to majors_price_data_ohlc and regime_price_data_ohlc.
        
        This is needed because backfill_from_hyperliquid writes to hyperliquid_price_data_ohlc,
        but we also need the data in majors_price_data_ohlc (for ALT composite) and
        regime_price_data_ohlc (for BTC regime driver).
        """
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=days)
        
        # Read from hyperliquid_price_data_ohlc
        result = (
            self.sb.table("hyperliquid_price_data_ohlc")
            .select("*")
            .eq("token", symbol)
            .eq("timeframe", timeframe)
            .gte("ts", start_time.isoformat())
            .order("ts", desc=False)
            .execute()
        )
        
        if not result.data:
            return
        
        # Transform to majors_price_data_ohlc format (for all majors)
        if symbol in MAJORS:
            majors_rows = []
            for row in result.data:
                majors_rows.append({
                    "token_contract": symbol,
                    "chain": "hyperliquid",
                    "timeframe": timeframe,
                    "timestamp": row["ts"],
                    "open_usd": float(row["open"]),
                    "high_usd": float(row["high"]),
                    "low_usd": float(row["low"]),
                    "close_usd": float(row["close"]),
                    "open_native": 0.0,
                    "high_native": 0.0,
                    "low_native": 0.0,
                    "close_native": 0.0,
                    "volume": float(row["volume"]),
                    "source": "hyperliquid",
                })
            
            # Batch upsert to majors_price_data_ohlc
            batch_size = 500
            for i in range(0, len(majors_rows), batch_size):
                batch = majors_rows[i:i + batch_size]
                try:
                    self.sb.table("majors_price_data_ohlc").upsert(
                        batch,
                        on_conflict="token_contract,chain,timeframe,timestamp"
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to sync {symbol} to majors_price_data_ohlc: {e}")
        
        # Transform to regime_price_data_ohlc format (for BTC only)
        if symbol in REGIME_DRIVERS:
            regime_rows = []
            for row in result.data:
                regime_rows.append({
                    "driver": symbol,
                    "timeframe": timeframe,
                    "timestamp": row["ts"],
                    "book_id": self.book_id,
                    "open_usd": float(row["open"]),
                    "high_usd": float(row["high"]),
                    "low_usd": float(row["low"]),
                    "close_usd": float(row["close"]),
                    "volume": float(row["volume"]),
                    "source": "hyperliquid",
                })
            
            # Batch upsert to regime_price_data_ohlc
            batch_size = 500
            for i in range(0, len(regime_rows), batch_size):
                batch = regime_rows[i:i + batch_size]
                try:
                    self.sb.table("regime_price_data_ohlc").upsert(
                        batch,
                        on_conflict="driver,book_id,timeframe,timestamp"
                    ).execute()
                except Exception as e:
                    logger.error(f"Failed to sync {symbol} to regime_price_data_ohlc: {e}")
    
    # Keep old method name for backward compatibility (deprecated)
    def backfill_majors_from_binance(
        self, 
        days: int = 90,
        timeframes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deprecated: Use backfill_majors_from_hyperliquid instead.
        
        This method is kept for backward compatibility but now calls
        the Hyperliquid backfill method.
        """
        logger.warning("backfill_majors_from_binance is deprecated, using Hyperliquid backfill instead")
        return self.backfill_majors_from_hyperliquid(days, timeframes)
    
    def collect_current_dominance(self) -> Tuple[float, float]:
        """
        Fetch current BTC.d and USDT.d from CoinGecko.
        
        Returns:
            Tuple of (btc_dominance, usdt_dominance) as percentages
        """
        data = self._fetch_json(f"{COINGECKO_BASE_URL}/global").get("data", {})
        mkt = data.get("market_cap_percentage", {}) or {}
        
        btc_d = float(mkt.get("btc", 0))
        usdt_d = float(mkt.get("usdt", 0))
        
        if btc_d == 0:
            raise RuntimeError("CoinGecko global missing btc dominance")
            
        # USDT might not be in market_cap_percentage, compute from market caps
        if usdt_d == 0:
            total_mc = (data.get("total_market_cap") or {}).get("usd")
            if total_mc:
                try:
                    tether = self._fetch_json(
                        f"{COINGECKO_BASE_URL}/coins/markets",
                        {"vs_currency": "usd", "ids": "tether"}
                    )
                    usdt_mc = float(tether[0].get("market_cap") or 0) if tether else 0
                    usdt_d = 100.0 * (usdt_mc / float(total_mc)) if usdt_mc else 0
                except Exception as e:
                    logger.warning(f"Failed to compute USDT.d: {e}")
        
        return btc_d, usdt_d
    
    def rollup_dominance_to_ohlc(self, timeframe: str = "1h") -> None:
        """
        Roll up 1m dominance points to OHLC bars.
        
        Args:
            timeframe: Target timeframe ('1h' or '1d')
        """
        if timeframe not in ["1h", "1d"]:
            raise ValueError(f"Invalid rollup timeframe: {timeframe}")
            
        for driver in ["BTC.d", "USDT.d"]:
            try:
                self._rollup_driver_ohlc(driver, "1m", timeframe)
                logger.info(f"Rolled up {driver} to {timeframe}")
            except Exception as e:
                logger.error(f"Failed to rollup {driver} to {timeframe}: {e}")
    
    # =========================================================================
    # Private: Binance API
    # =========================================================================
    
    def _fetch_binance_klines(
        self,
        symbol: str,
        interval: str,
        days: int = 90
    ) -> List[OHLCBar]:
        """Fetch klines from Binance with batching for large requests"""
        bars: List[OHLCBar] = []
        
        # Calculate candles needed
        if interval == "1m":
            candles_needed = days * 24 * 60
        elif interval == "1h":
            candles_needed = days * 24
        elif interval == "1d":
            candles_needed = days
        else:
            raise ValueError(f"Unknown interval: {interval}")
        
        batches_needed = (candles_needed + 999) // 1000
        now = datetime.now(timezone.utc)
        end_time = int(now.timestamp() * 1000)
        
        for _ in range(batches_needed):
            url = f"{BINANCE_BASE_URL}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": 1000,
                "endTime": end_time,
            }
            
            try:
                data = self._fetch_json(url, params)
                if not data:
                    break
                    
                for candle in data:
                    bar = OHLCBar(
                        timestamp=datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=float(candle[5]),
                    )
                    bars.append(bar)
                
                # Move end_time back for next batch
                if data:
                    end_time = int(data[0][0]) - 1
                    
                time.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                logger.error(f"Binance API error: {e}")
                break
        
        # Sort by timestamp ascending
        bars.sort(key=lambda b: b.timestamp)
        return bars
    
    def _write_major_bars(self, driver: str, timeframe: str, bars: List[OHLCBar]) -> None:
        """Write major bars to regime_price_data_ohlc"""
        if not bars:
            return
            
        rows = []
        for bar in bars:
            rows.append({
                "driver": driver,
                "timeframe": timeframe,
                "book_id": self.book_id,
                "timestamp": bar.timestamp.isoformat(),
                "open_usd": bar.open,
                "high_usd": bar.high,
                "low_usd": bar.low,
                "close_usd": bar.close,
                "volume": bar.volume,
                "source": "binance",
            })
        
        # Upsert in batches
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                self.sb.table("regime_price_data_ohlc").upsert(
                    batch,
                    on_conflict="driver,book_id,timeframe,timestamp"
                ).execute()
            except Exception as e:
                # Log to file only, don't print to terminal
                logger.error(f"Failed to write batch for {driver}/{timeframe}: {e}", exc_info=True)
    
    def _write_majors_ohlc(self, contract: str, timeframe: str, bars: List[OHLCBar]) -> None:
        """Write major bars to majors_price_data_ohlc (for SOL/ETH/BNB used in ALT composite).
        
        Note: 'chain' field represents the SOURCE (binance/hyperliquid), not the blockchain.
        This allows us to track where price data came from.
        """
        if not bars:
            return
        
        rows = []
        for bar in bars:
            rows.append({
                "token_contract": contract,
                "chain": "binance",  # Source: Binance API (not blockchain)
                "timeframe": timeframe,
                "timestamp": bar.timestamp.isoformat(),
                "open_native": 0.0,  # Not used for majors
                "high_native": 0.0,
                "low_native": 0.0,
                "close_native": 0.0,
                "open_usd": bar.open,
                "high_usd": bar.high,
                "low_usd": bar.low,
                "close_usd": bar.close,
                "volume": bar.volume,
                "source": "binance",
            })
        
        # Upsert in batches
        batch_size = 500
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                self.sb.table("majors_price_data_ohlc").upsert(
                    batch,
                    on_conflict="token_contract,chain,timeframe,timestamp"
                ).execute()
            except Exception as e:
                logger.error(f"Failed to write majors batch for {contract}/{timeframe}: {e}", exc_info=True)
    
    # =========================================================================
    # Private: Composite Calculations
    # =========================================================================
    
    def _collect_majors(self, timeframe: str) -> None:
        """Collect current major prices and compute ALT composite"""
        # Read latest majors from majors_price_data_ohlc
        now = datetime.now(timezone.utc)
        bucket_start = self._get_bucket_start(now, timeframe)
        
        # Only write BTC as a driver (SOL/ETH/BNB are only used for ALT composite)
        try:
            bar = self._get_latest_major_bar("BTC", timeframe, bucket_start)
            if bar:
                self._write_major_bars("BTC", timeframe, [bar])
                logger.info(f"Wrote BTC bar to regime_price_data_ohlc for {timeframe} at {bar.timestamp.isoformat()}")
            else:
                logger.warning(f"No BTC bar found in majors_price_data_ohlc for {timeframe} (checked from {bucket_start.isoformat()})")
        except Exception as e:
            logger.error(f"Failed to get BTC from majors: {e}", exc_info=True)
        
        # Compute ALT composite (reads from majors_price_data_ohlc, not regime_price_data_ohlc)
        try:
            self._compute_alt_composite(timeframe, days=1)
            logger.info(f"ALT composite computed and written to regime_price_data_ohlc for {timeframe}")
        except Exception as e:
            logger.error(f"Failed to compute ALT composite for {timeframe}: {e}", exc_info=True)
    
    def _get_latest_major_bar(
        self, 
        symbol: str, 
        timeframe: str,
        bucket_start: datetime
    ) -> Optional[OHLCBar]:
        """Get latest bar from majors_price_data_ohlc
        
        Uses uppercase symbols (BTC, SOL, ETH, BNB) to match Hyperliquid naming.
        Doesn't filter by chain - gets latest bar which will naturally be from Hyperliquid
        (ongoing) or Binance (backfill data from startup).
        """
        # Query for latest bar with uppercase symbol (no chain filter)
        # Latest will naturally be from Hyperliquid (ongoing) or Binance (startup backfill)
        result = (
            self.sb.table("majors_price_data_ohlc")
            .select("*")
            .eq("token_contract", symbol)  # Uppercase: BTC, SOL, ETH, BNB
            .eq("timeframe", timeframe)
            .gte("timestamp", bucket_start.isoformat())
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        
        if result.data:
            row = result.data[0]
            return OHLCBar(
                timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                open=float(row["open_usd"]),
                high=float(row["high_usd"]),
                low=float(row["low_usd"]),
                close=float(row["close_usd"]),
                volume=float(row.get("volume", 0)),
            )
        
        # Fallback to legacy lowercase names (for old Binance backfill data before normalization)
        legacy_names = {
            "BTC": "bitcoin",
            "SOL": "solana",
            "ETH": "ethereum",
            "BNB": "bnb",
        }
        legacy_name = legacy_names.get(symbol)
        if legacy_name:
            result_legacy = (
                self.sb.table("majors_price_data_ohlc")
                .select("*")
                .eq("token_contract", legacy_name)  # Legacy: bitcoin, solana, ethereum, bnb
                .eq("timeframe", timeframe)
                .gte("timestamp", bucket_start.isoformat())
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            
            if result_legacy.data:
                row = result_legacy.data[0]
                return OHLCBar(
                    timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                    open=float(row["open_usd"]),
                    high=float(row["high_usd"]),
                    low=float(row["low_usd"]),
                    close=float(row["close_usd"]),
                    volume=float(row.get("volume", 0)),
                )
        
        return None
    
    def _compute_alt_composite(self, timeframe: str, days: int = 1) -> None:
        """
        Compute ALT composite from SOL, ETH, BNB, HYPE.
        
        Note: HYPE is only available from Hyperliquid WS (not Binance), so it may be missing
        during backfill. ALT composite will work with SOL/ETH/BNB if HYPE is unavailable.
        
        Methodology:
        - open = avg(opens)
        - high = max(highs)
        - low = min(lows)
        - close = avg(closes)
        - volume = sum(volumes)
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        
        # Fetch all component bars from majors_price_data_ohlc (not regime_price_data_ohlc)
        # Both Binance and Hyperliquid now use uppercase symbols (SOL, ETH, BNB, HYPE)
        # Note: HYPE is only available from Hyperliquid, not Binance
        component_bars: Dict[str, List[Dict]] = {}
        for component in ALT_COMPONENTS:
            # Query for ALT components from both Binance (backfill) and Hyperliquid (live)
            # Chain field represents SOURCE (binance/hyperliquid), not blockchain
            # Both sources now use uppercase symbols (SOL, ETH, BNB), but check old lowercase names too
            result_binance = None
            if component != "HYPE":  # HYPE not available from Binance
                # Try new uppercase naming first (going forward)
                result_binance = (
                    self.sb.table("majors_price_data_ohlc")
                    .select("*")
                    .eq("token_contract", component)  # Uppercase: SOL, ETH, BNB
                    .eq("chain", "binance")
                    .eq("timeframe", timeframe)
                    .gte("timestamp", start.isoformat())
                    .order("timestamp", desc=False)
                    .execute()
                )
                # Fallback to old lowercase names for historical data (legacy support)
                if not result_binance.data:
                    old_names = {"SOL": "solana", "ETH": "ethereum", "BNB": "bnb"}
                    old_name = old_names.get(component)
                    if old_name:
                        result_binance_legacy = (
                            self.sb.table("majors_price_data_ohlc")
                            .select("*")
                            .eq("token_contract", old_name)  # Legacy: solana, ethereum, bnb
                            .eq("chain", "binance")
                            .eq("timeframe", timeframe)
                            .gte("timestamp", start.isoformat())
                            .order("timestamp", desc=False)
                            .execute()
                        )
                        if result_binance_legacy.data:
                            result_binance = result_binance_legacy
            
            result_hyperliquid = (
                self.sb.table("majors_price_data_ohlc")
                .select("*")
                .eq("token_contract", component)  # Use uppercase symbol directly
                .eq("chain", "hyperliquid")  # Hyperliquid WS data
                .eq("timeframe", timeframe)
                .gte("timestamp", start.isoformat())
                .order("timestamp", desc=False)
                .execute()
            )
            
            # Combine results (prefer Hyperliquid if both exist, as it's more recent)
            result_data = []
            if result_hyperliquid and result_hyperliquid.data:
                result_data.extend(result_hyperliquid.data)
            if result_binance and result_binance.data:
                result_data.extend(result_binance.data)
            
            # Create a mock result object with combined data
            class MockResult:
                def __init__(self, data):
                    self.data = data
            result = MockResult(result_data)
            if result.data:
                component_bars[component] = result.data
        
        # Require at least 3 components (SOL/ETH/BNB) - HYPE is optional since it's not on Binance
        min_required = 3
        if len(component_bars) < min_required:
            missing = [c for c in ALT_COMPONENTS if c not in component_bars]
            # Check if data exists but wasn't found (wrong contract names?)
            logger.warning(f"Missing ALT components for {timeframe}: {missing} (found: {list(component_bars.keys())}, need at least {min_required})")
            # Try to diagnose: check if any data exists for these contracts
            for component in missing:
                if component != "HYPE":  # HYPE is expected to be missing
                    # Check both binance and hyperliquid sources (both use uppercase symbols now)
                    test_binance = (
                        self.sb.table("majors_price_data_ohlc")
                        .select("token_contract, chain, timeframe, timestamp")
                        .eq("token_contract", component)
                        .eq("chain", "binance")
                        .limit(1)
                        .execute()
                    )
                    test_hyperliquid = (
                        self.sb.table("majors_price_data_ohlc")
                        .select("token_contract, chain, timeframe, timestamp")
                        .eq("token_contract", component)
                        .eq("chain", "hyperliquid")
                        .limit(1)
                        .execute()
                    )
                    if (test_binance and test_binance.data) or (test_hyperliquid and test_hyperliquid.data):
                        sources = []
                        if test_binance and test_binance.data:
                            sources.append("binance")
                        if test_hyperliquid and test_hyperliquid.data:
                            sources.append("hyperliquid")
                        logger.warning(f"  {component} data exists ({', '.join(sources)}) but not for timeframe {timeframe}")
                    else:
                        logger.warning(f"  {component} data not found in majors_price_data_ohlc (contract: {component})")
            # Log details about what we found
            for component, bars in component_bars.items():
                logger.debug(f"  {component}: {len(bars)} bars")
            return
        
        # If HYPE is missing, log but continue with SOL/ETH/BNB
        if "HYPE" not in component_bars:
            logger.info(f"HYPE not available for ALT composite {timeframe} (only available from Hyperliquid WS, will use SOL/ETH/BNB)")
        
        # If HYPE is missing, log but continue with SOL/ETH/BNB
        if "HYPE" not in component_bars:
            logger.info(f"HYPE not available for ALT composite {timeframe} (only available from Hyperliquid WS)")
        
        # Group by timestamp and compute composite
        timestamp_bars: Dict[str, Dict[str, List[float]]] = {}
        for component, bars in component_bars.items():
            for bar in bars:
                ts = bar["timestamp"]
                if ts not in timestamp_bars:
                    timestamp_bars[ts] = {"opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
                timestamp_bars[ts]["opens"].append(float(bar["open_usd"]))
                timestamp_bars[ts]["highs"].append(float(bar["high_usd"]))
                timestamp_bars[ts]["lows"].append(float(bar["low_usd"]))
                timestamp_bars[ts]["closes"].append(float(bar["close_usd"]))
                timestamp_bars[ts]["volumes"].append(float(bar.get("volume", 0)))
        
        # Write composite bars
        rows = []
        for ts, data in timestamp_bars.items():
            # Require at least 3 components (SOL/ETH/BNB) - HYPE is optional
            if len(data["opens"]) < min_required:
                continue  # Skip incomplete bars
            rows.append({
                "driver": "ALT",
                "timeframe": timeframe,
                "book_id": self.book_id,
                "timestamp": ts,
                "open_usd": sum(data["opens"]) / len(data["opens"]),
                "high_usd": max(data["highs"]),
                "low_usd": min(data["lows"]),
                "close_usd": sum(data["closes"]) / len(data["closes"]),
                "volume": sum(data["volumes"]),
                "source": "composite",
                "component_count": len(data["opens"]),
            })
        
        if rows:
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                self.sb.table("regime_price_data_ohlc").upsert(
                    batch,
                    on_conflict="driver,book_id,timeframe,timestamp"
                ).execute()
            logger.info(f"Wrote {len(rows)} ALT composite bars for {timeframe}")
    
    def _collect_bucket_composites(self, timeframe: str) -> None:
        """
        Compute bucket composite OHLC from lowcap positions.
        
        Buckets: nano, small, mid, big
        """
        now = datetime.now(timezone.utc)
        bucket_start = self._get_bucket_start(now, timeframe)
        
        # Get tokens by bucket from token_cap_bucket
        bucket_tokens = self._get_tokens_by_bucket()
        
        for bucket_name, tokens in bucket_tokens.items():
            try:
                # Skip empty buckets early to save computation
                if not tokens:
                    logger.debug(f"Skipping {bucket_name} bucket: no tokens")
                    continue
                
                bar = self._compute_bucket_bar(bucket_name, tokens, timeframe, bucket_start)
                if bar:
                    self._write_bucket_bar(bucket_name, timeframe, bar, len(tokens))
            except Exception as e:
                logger.warning(f"Failed to compute {bucket_name} bucket: {e}")
    
    def _get_tokens_by_bucket(self) -> Dict[str, List[Dict]]:
        """Get tokens grouped by market cap bucket"""
        result = (
            self.sb.table("token_cap_bucket")
            .select("token_contract,chain,bucket,market_cap_usd")
            .execute()
        )
        
        buckets: Dict[str, List[Dict]] = {
            "nano": [], "small": [], "mid": [], "big": []
        }
        
        for row in result.data or []:
            bucket = row.get("bucket", "")
            mc = float(row.get("market_cap_usd", 0))
            
            # Determine bucket from market cap
            for bucket_name, (min_mc, max_mc) in BUCKET_THRESHOLDS.items():
                if min_mc <= mc < max_mc:
                    buckets[bucket_name].append({
                        "token_contract": row["token_contract"],
                        "chain": row["chain"],
                        "market_cap_usd": mc,
                    })
                    break
        
        return buckets
    
    def _compute_bucket_bar(
        self,
        bucket: str,
        tokens: List[Dict],
        timeframe: str,
        bucket_start: datetime
    ) -> Optional[OHLCBar]:
        """Compute composite OHLC for a bucket"""
        if not tokens:
            return None
            
        opens, highs, lows, closes, volumes = [], [], [], [], []
        
        for token in tokens[:64]:  # Limit to top 64 by mcap
            bar = self._get_token_bar(
                token["token_contract"],
                token["chain"],
                timeframe,
                bucket_start
            )
            if bar:
                opens.append(bar["open_usd"])
                highs.append(bar["high_usd"])
                lows.append(bar["low_usd"])
                closes.append(bar["close_usd"])
                volumes.append(bar.get("volume", 0))
        
        if len(opens) < 1:
            return None
        
        return OHLCBar(
            timestamp=bucket_start,
            open=sum(opens) / len(opens),
            high=max(highs),
            low=min(lows),
            close=sum(closes) / len(closes),
            volume=sum(volumes),
        )
    
    def _get_token_bar(
        self,
        token_contract: str,
        chain: str,
        timeframe: str,
        bucket_start: datetime
    ) -> Optional[Dict]:
        """Get OHLC bar for a token"""
        # Add 5-minute lookback to account for data latency (1-2 min behind)
        lookback_start = bucket_start - timedelta(minutes=5)
        result = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("*")
            .eq("token_contract", token_contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .gte("timestamp", lookback_start.isoformat())
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        
        if result.data:
            row = result.data[0]
            return {
                "open_usd": float(row["open_usd"]),
                "high_usd": float(row["high_usd"]),
                "low_usd": float(row["low_usd"]),
                "close_usd": float(row["close_usd"]),
                "volume": float(row.get("volume", 0)),
            }
        return None
    
    def _write_bucket_bar(
        self,
        bucket: str,
        timeframe: str,
        bar: OHLCBar,
        component_count: int
    ) -> None:
        """Write bucket composite bar"""
        row = {
            "driver": bucket,
            "timeframe": timeframe,
            "book_id": self.book_id,
            "timestamp": bar.timestamp.isoformat(),
            "open_usd": bar.open,
            "high_usd": bar.high,
            "low_usd": bar.low,
            "close_usd": bar.close,
            "volume": bar.volume,
            "source": "composite",
            "component_count": component_count,
        }
        self.sb.table("regime_price_data_ohlc").upsert(
            [row],
            on_conflict="driver,book_id,timeframe,timestamp"
        ).execute()
    
    # =========================================================================
    # Private: Dominance
    # =========================================================================
    
    def _collect_dominance(self) -> None:
        """Collect current dominance and store as 1m bar"""
        btc_d, usdt_d = self.collect_current_dominance()
        now = datetime.now(timezone.utc)
        bucket_start = self._get_bucket_start(now, "1m")
        
        # Store dominance percentages as "prices" (1-100% = $1-$100)
        for driver, value in [("BTC.d", btc_d), ("USDT.d", usdt_d)]:
            row = {
                "driver": driver,
                "timeframe": "1m",
                "book_id": self.book_id,
                "timestamp": bucket_start.isoformat(),
                "open_usd": value,
                "high_usd": value,
                "low_usd": value,
                "close_usd": value,
                "volume": 0,
                "source": "coingecko",
            }
            self.sb.table("regime_price_data_ohlc").upsert(
                [row],
                on_conflict="driver,book_id,timeframe,timestamp"
            ).execute()
        
        logger.info(f"Collected dominance: BTC.d={btc_d:.2f}%, USDT.d={usdt_d:.2f}%")
    
    def _rollup_driver_ohlc(
        self,
        driver: str,
        source_tf: str,
        target_tf: str
    ) -> None:
        """Roll up OHLC bars from source to target timeframe"""
        now = datetime.now(timezone.utc)
        target_start = self._get_bucket_start(now, target_tf)
        
        # Determine lookback based on target timeframe
        if target_tf == "1h":
            lookback = timedelta(hours=1)
        elif target_tf == "1d":
            lookback = timedelta(days=1)
        else:
            return
        
        source_start = target_start - lookback
        
        # Fetch source bars
        result = (
            self.sb.table("regime_price_data_ohlc")
            .select("*")
            .eq("driver", driver)
            .eq("book_id", self.book_id)
            .eq("timeframe", source_tf)
            .gte("timestamp", source_start.isoformat())
            .lt("timestamp", target_start.isoformat())
            .order("timestamp", desc=False)
            .execute()
        )
        
        if not result.data:
            return
        
        # Compute OHLC from source bars
        opens = [float(r["open_usd"]) for r in result.data]
        highs = [float(r["high_usd"]) for r in result.data]
        lows = [float(r["low_usd"]) for r in result.data]
        closes = [float(r["close_usd"]) for r in result.data]
        volumes = [float(r.get("volume", 0)) for r in result.data]
        
        row = {
            "driver": driver,
            "timeframe": target_tf,
            "book_id": self.book_id,
            "timestamp": target_start.isoformat(),
            "open_usd": opens[0],
            "high_usd": max(highs),
            "low_usd": min(lows),
            "close_usd": closes[-1],
            "volume": sum(volumes),
            "source": "rollup",
        }
        
        self.sb.table("regime_price_data_ohlc").upsert(
            [row],
            on_conflict="driver,book_id,timeframe,timestamp"
        ).execute()
    
    # =========================================================================
    # Private: Utilities
    # =========================================================================
    
    def _get_bucket_start(self, dt: datetime, timeframe: str) -> datetime:
        """Get the start of the current bucket for a timeframe"""
        if timeframe == "1m":
            return dt.replace(second=0, microsecond=0)
        elif timeframe == "1h":
            return dt.replace(minute=0, second=0, microsecond=0)
        elif timeframe == "1d":
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Unknown timeframe: {timeframe}")
    
    def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Any:
        """Fetch JSON from URL"""
        if params:
            url = f"{url}?{urlencode(params)}"
        req = Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "LotusTrader/1.0"
        })
        with urlopen(req, timeout=20) as resp:  # nosec - public API
            return json.loads(resp.read().decode("utf-8"))


# =========================================================================
# CLI Entry Point
# =========================================================================

def main() -> None:
    """CLI entry point for regime price collection"""
    import argparse
    
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Regime Price Collector")
    parser.add_argument("--backfill", action="store_true", help="Backfill historical data from Binance")
    parser.add_argument("--days", type=int, default=90, help="Days to backfill (default: 90)")
    parser.add_argument("--timeframe", type=str, default="1h", help="Timeframe to collect (default: 1h)")
    parser.add_argument("--dominance", action="store_true", help="Collect current dominance only")
    args = parser.parse_args()
    
    collector = RegimePriceCollector()
    
    if args.backfill:
        results = collector.backfill_majors_from_binance(days=args.days)
        print(f"Backfill complete: {results}")
    elif args.dominance:
        btc_d, usdt_d = collector.collect_current_dominance()
        print(f"BTC.d: {btc_d:.2f}%, USDT.d: {usdt_d:.2f}%")
    else:
        results = collector.run(timeframe=args.timeframe)
        print(f"Collection complete: {results}")


if __name__ == "__main__":
    main()

