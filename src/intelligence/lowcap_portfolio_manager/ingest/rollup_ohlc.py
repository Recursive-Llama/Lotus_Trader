"""
Generic OHLC Rollup System

Converts 1m price points to 1m OHLC bars and rolls up to higher timeframes (5m, 15m, 1h, 4h, 1d) for both majors and lowcaps.

Input Sources:
- majors_price_data_1m (already OHLC bars)
- lowcap_price_data_1m (price points, needs OHLC conversion)

Output Tables:
- majors_price_data_ohlc
- lowcap_price_data_ohlc

Timeframes: 1m, 5m, 15m, 1h, 4h, 1d
Prices: Both native and USD prices
Volume: Sum of 1m volumes for timeframe

1m OHLC Conversion (CRITICAL - different from rollup):
- Open = Previous candle's close (or first price if no previous)
- Close = Current price
- High = max(open, close)
- Low = min(open, close)
- This is creating OHLC from price points, not rolling up to higher timeframe
"""

from __future__ import annotations

import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger("rollup")


class DataSource(Enum):
    """Data source types"""
    MAJORS = "majors"
    LOWCAPS = "lowcaps"


class Timeframe(Enum):
    """Supported timeframes"""
    M1 = "1m"  # Special case: converts price points to OHLC bars
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


@dataclass
class OHLCBar:
    """OHLC bar data structure"""
    token_contract: str
    chain: str
    timeframe: str
    timestamp: datetime
    
    # Native prices (for decisions)
    open_native: float
    high_native: float
    low_native: float
    close_native: float
    
    # USD prices (for analysis)
    open_usd: float
    high_usd: float
    low_usd: float
    close_usd: float
    
    # Volume
    volume: float
    
    # Market data snapshots
    liquidity_usd: float = 0.0
    liquidity_change_1m: float = 0.0
    price_change_24h: float = 0.0
    market_cap: float = 0.0
    fdv: float = 0.0
    dex_id: Optional[str] = None
    pair_address: Optional[str] = None
    
    # Metadata
    source: str = "rollup"
    partial: bool = False
    coverage_pct: float = 100.0
    bars_used: int = 0
    expected_bars: int = 0


class GenericOHLCRollup:
    """Generic OHLC rollup system for both majors and lowcaps"""
    
    # Rate limit for price collection (matching scheduled_price_collector)
    MAX_CALLS_PER_MINUTE = 250
    
    def __init__(self):
        """Initialize the rollup system"""
        # Load environment variables from the correct path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        env_path = os.path.join(project_root, '.env')
        load_dotenv(env_path)
        
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        
        self.sb: Client = create_client(supabase_url, supabase_key)
        self.logger = logging.getLogger("rollup")
        # GeckoTerminal fallback budget
        self.gt_budget_per_minute = int(os.getenv("GT_CALL_BUDGET", "20"))
        self.gt_calls_remaining = self.gt_budget_per_minute
        self.last_gt_budget_reset: Optional[datetime] = None
        
        # Cache for dynamic threshold calculation
        self._cached_token_count: Optional[int] = None
        self._cached_token_count_time: Optional[datetime] = None
    
    def _get_total_token_count(self) -> int:
        """Get total unique token count for dynamic threshold calculation"""
        # Cache for 5 minutes to avoid repeated queries
        now = datetime.now(timezone.utc)
        if (self._cached_token_count is not None and 
            self._cached_token_count_time is not None and
            (now - self._cached_token_count_time).total_seconds() < 300):
            return self._cached_token_count
        
        try:
            result = (
                self.sb.table('lowcap_positions')
                .select('token_contract', 'token_chain')
                .in_('status', ['active', 'watchlist', 'dormant'])
                .execute()
            )
            
            # Count unique (token_contract, chain) pairs
            unique_tokens = set()
            for row in (result.data or []):
                token = row.get('token_contract')
                chain = row.get('token_chain', '').lower()
                if token and chain:
                    unique_tokens.add((token, chain))
            
            self._cached_token_count = len(unique_tokens)
            self._cached_token_count_time = now
            return self._cached_token_count
        except Exception as e:
            self.logger.warning(f"Error getting token count: {e}")
            return self._cached_token_count or 100  # Default fallback
    
    def _get_collection_interval(self) -> int:
        """
        Calculate collection interval based on total token count.
        
        Returns interval in minutes (1, 2, 3, etc.)
        - 0-250 tokens: Every 1 min
        - 250-500 tokens: Every 2 min
        - 500-750 tokens: Every 3 min
        - etc.
        """
        total_tokens = self._get_total_token_count()
        if total_tokens <= 0:
            return 1
        return max(1, math.ceil(total_tokens / self.MAX_CALLS_PER_MINUTE))
    
    def _get_dynamic_coverage_threshold(self) -> float:
        """
        Calculate coverage threshold based on collection interval.
        
        Returns threshold as decimal (0.50, 0.40, 0.33, etc.)
        - Interval 1: 50% (was 60%)
        - Interval 2: 40% (was 45%)
        - Interval 3: 33%
        - Interval 4: 25%
        - Interval 5+: 20% minimum
        
        Lower thresholds allow more tokens with less frequent collection,
        since we're now trading on 15m timeframe (not 1m).
        """
        interval = self._get_collection_interval()
        if interval <= 1:
            return 0.50  # 50% for every-minute collection
        elif interval == 2:
            return 0.40  # 40% for every-2-minute collection
        elif interval == 3:
            return 0.33  # 33% for every-3-minute collection
        elif interval == 4:
            return 0.25  # 25% for every-4-minute collection
        else:
            return 0.20  # 20% minimum for 5+ minute collection

    def _reset_gt_budget_if_needed(self):
        now = datetime.now(timezone.utc)
        if self.last_gt_budget_reset is None or (now - self.last_gt_budget_reset).total_seconds() >= 60:
            self.gt_calls_remaining = self.gt_budget_per_minute
            self.last_gt_budget_reset = now

    def _attempt_gt_backfill(self, token_contract: str, chain: str, timeframe: Timeframe, boundary_ts: datetime) -> bool:
        """
        Try to backfill a specific boundary via GeckoTerminal.
        Returns True if attempted and possibly inserted rows, False otherwise.
        """
        try:
            from src.intelligence.lowcap_portfolio_manager.jobs.geckoterminal_backfill import backfill_token_timeframe
        except Exception as e:
            self.logger.warning(f"GT backfill module unavailable: {e}")
            return False

        self._reset_gt_budget_if_needed()
        if self.gt_calls_remaining <= 0:
            self.logger.info(f"GT budget exhausted, skipping GT backfill for {token_contract[:8]}.../{chain} {timeframe.value} @ {boundary_ts}")
            return False

        self.gt_calls_remaining -= 1
        tf_minutes = self._get_timeframe_minutes(timeframe)
        lookback_minutes = max(tf_minutes * 2, 30)
        self.logger.info(
            f"GT backfill attempt for {token_contract[:8]}.../{chain} {timeframe.value} at {boundary_ts} "
            f"(lookback {lookback_minutes}m, remaining budget={self.gt_calls_remaining})"
        )
        try:
            result = backfill_token_timeframe(
                token_contract=token_contract,
                chain=chain,
                timeframe=timeframe.value,
                lookback_minutes=lookback_minutes,
            )
            if result.get("inserted_rows", 0) > 0:
                self.logger.info(
                    f"GT backfill inserted {result.get('inserted_rows')} rows for {token_contract[:8]}.../{chain} {timeframe.value}"
                )
                return True
        except Exception as e:
            self.logger.warning(
                f"GT backfill failed for {token_contract[:8]}.../{chain} {timeframe.value} at {boundary_ts}: {e}"
            )
        return False
    
    def rollup_timeframe(
        self, 
        data_source: DataSource, 
        timeframe: Timeframe,
        when: Optional[datetime] = None
    ) -> int:
        """
        Roll up data for a specific timeframe
        
        Args:
            data_source: MAJORS or LOWCAPS
            timeframe: Target timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            when: Timestamp to rollup (default: now)
            
        Returns:
            Number of bars written
        """
        if when is None:
            when = datetime.now(tz=timezone.utc)
        
        # Normalize timeframe value for robustness (some callers may pass str instead of Timeframe)
        tf_value = timeframe.value if isinstance(timeframe, Timeframe) else str(timeframe)
        
        # For 1m, just convert price points immediately (no boundary check needed)
        if tf_value == Timeframe.M1.value:
            if data_source == DataSource.MAJORS:
                # Majors already have OHLC data, skip 1m conversion
                self.logger.info("Majors data already in OHLC format, skipping 1m conversion")
                return 0
            else:
                # Get unprocessed price points for 1m OHLC conversion
                self.logger.info(f"Starting 1m OHLC conversion at {when}")
                bars = self._get_lowcap_1m_data(timeframe, when)
                if not bars:
                    self.logger.info(f"No unprocessed price points found for 1m OHLC conversion")
                    return 0
                
                # Log summary of price points found
                points_by_token = defaultdict(int)
                timestamp_range = {"min": None, "max": None}
                for bar in bars:
                    key = (bar['token_contract'], bar['chain'])
                    points_by_token[key] += 1
                    ts = datetime.fromisoformat(bar['timestamp'].replace('Z', '+00:00'))
                    if timestamp_range["min"] is None or ts < timestamp_range["min"]:
                        timestamp_range["min"] = ts
                    if timestamp_range["max"] is None or ts > timestamp_range["max"]:
                        timestamp_range["max"] = ts
                
            # Alert if freshest data is stale (>5 minutes behind now)
            age_minutes = (when - timestamp_range["max"]).total_seconds() / 60 if timestamp_range["max"] else 999
            if age_minutes > 5:
                self.logger.warning(
                    f"1m OHLC conversion using stale price points: latest={timestamp_range['max']}, "
                    f"age={age_minutes:.1f}m, earliest={timestamp_range['min']}, count={len(bars)}"
                )
            
            # Log summary (always, not just when stale)
            self.logger.info(
                f"Found {len(bars)} unprocessed price points across {len(points_by_token)} tokens "
                f"(range: {timestamp_range['min']} to {timestamp_range['max']})"
            )
            
            # Log per-token breakdown (first 20 tokens)
            token_list = sorted(points_by_token.items())[:20]
            for (token_contract, chain), count in token_list:
                self.logger.info(f"  - {token_contract[:8]}.../{chain}: {count} price points")
            if len(points_by_token) > 20:
                self.logger.info(f"  ... (+{len(points_by_token) - 20} more tokens)")
            
            # Convert price points to 1m OHLC bars
            ohlc_bars = self._convert_1m_to_ohlc(bars)
            if not ohlc_bars:
                self.logger.warning(f"1m OHLC conversion created 0 bars from {len(bars)} price points")
                return 0
            
            # Log conversion summary
            bars_by_token = defaultdict(int)
            for bar in ohlc_bars:
                key = (bar.token_contract, bar.chain)
                bars_by_token[key] += 1
            
            self.logger.info(
                f"Converted {len(bars)} price points to {len(ohlc_bars)} 1m OHLC bars "
                f"across {len(bars_by_token)} tokens"
            )
            
            # Store to database
            written = self._store_ohlc_bars(data_source, ohlc_bars)
            
            if written != len(ohlc_bars):
                self.logger.warning(
                    f"1m OHLC conversion: created {len(ohlc_bars)} bars but wrote {written} to database"
                )
            else:
                self.logger.info(
                    f"1m OHLC conversion complete: wrote {written} bars to database "
                    f"({len(bars_by_token)} tokens)"
                )
            
            # Warn if freshest 1m OHLC is stale (>5 minutes old)
            try:
                latest = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("timestamp")
                    .eq("timeframe", "1m")
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                if latest.data:
                    latest_ts = datetime.fromisoformat(latest.data[0]["timestamp"].replace("Z", "+00:00"))
                    age_minutes = (when - latest_ts).total_seconds() / 60
                    if age_minutes > 5:
                        self.logger.warning(
                            f"Freshest 1m OHLC is stale: latest={latest_ts}, age={age_minutes:.1f}m"
                        )
            except Exception as e:
                self.logger.warning(f"Failed to check 1m OHLC freshness: {e}")
            
            return written
        
        # For higher timeframes, check if we're at a boundary (with tolerance for late runs)
        boundary_ts = self._get_timeframe_boundary_ts(when, timeframe)
        is_at_boundary = self._is_at_timeframe_boundary(when, timeframe)
        
        # Allow processing if we're within 2 minutes of the boundary (for late runs or catch-up)
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        tolerance_minutes = min(2, timeframe_minutes // 2)  # At most 2 minutes, or half the timeframe
        time_since_boundary = (when - boundary_ts).total_seconds() / 60
        
        if not is_at_boundary and time_since_boundary > tolerance_minutes:
            self.logger.info(f"Not at {timeframe.value} boundary (when={when}, boundary={boundary_ts}, {time_since_boundary:.1f}m since boundary), skipping rollup")
            return 0
        
        # If we're past the boundary but within tolerance, log it
        if not is_at_boundary and time_since_boundary <= tolerance_minutes:
            self.logger.info(f"Processing {timeframe.value} rollup {time_since_boundary:.1f} minutes after boundary (tolerance: {tolerance_minutes}m)")
        
        self.logger.info(f"Rolling up {data_source.value} data to {timeframe.value} at {when} (boundary: {boundary_ts})")
        
        # Get 1m data for the timeframe window
        # Use boundary_ts as the end point to ensure we get the correct window
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        start_time = boundary_ts - timedelta(minutes=timeframe_minutes * 2)
        
        self.logger.info(
            f"Querying 1m data for {timeframe.value} rollup: "
            f"boundary={boundary_ts}, window={start_time} to {boundary_ts} ({timeframe_minutes * 2} minutes)"
        )
        
        if data_source == DataSource.MAJORS:
            bars = self._get_majors_1m_data(timeframe, boundary_ts)
        else:
            bars = self._get_lowcap_1m_data(timeframe, boundary_ts)  # Use boundary_ts for consistency
        
        if not bars:
            self.logger.warning(
                f"No 1m data found for {data_source.value} {timeframe.value} rollup at {boundary_ts} "
                f"(window: {start_time} to {boundary_ts})"
            )
            return 0
        
        # Log data query results
        bars_by_token = defaultdict(int)
        timestamp_range = {"min": None, "max": None}
        for bar in bars:
            key = (bar['token_contract'], bar['chain'])
            bars_by_token[key] += 1
            ts = datetime.fromisoformat(bar['timestamp'].replace('Z', '+00:00'))
            if timestamp_range["min"] is None or ts < timestamp_range["min"]:
                timestamp_range["min"] = ts
            if timestamp_range["max"] is None or ts > timestamp_range["max"]:
                timestamp_range["max"] = ts
        
        self.logger.info(
            f"Found {len(bars)} 1m bars across {len(bars_by_token)} tokens "
            f"(range: {timestamp_range['min']} to {timestamp_range['max']})"
        )
        
        # Log per-token breakdown (first 10 tokens)
        token_list = sorted(bars_by_token.items(), key=lambda x: x[1], reverse=True)[:10]
        for (token_contract, chain), count in token_list:
            self.logger.info(f"  - {token_contract[:8]}.../{chain}: {count} 1m bars")
        if len(bars_by_token) > 10:
            self.logger.info(f"  ... (+{len(bars_by_token) - 10} more tokens)")
        
        # Check if we have enough bars (dynamic threshold based on collection interval)
        required_bars = self._get_required_bars_count(timeframe)
        coverage_threshold = self._get_dynamic_coverage_threshold()
        min_required_bars = max(1, int(required_bars * coverage_threshold))  # Dynamic threshold
        
        # Calculate per-token coverage
        token_coverage = defaultdict(lambda: {"bars": 0, "tokens": set()})
        for bar in bars:
            key = (bar['token_contract'], bar['chain'])
            token_coverage[key]["bars"] += 1
        
        # Log tokens with insufficient data
        insufficient_tokens = []
        for (token_contract, chain), data in token_coverage.items():
            if data["bars"] < min_required_bars:
                insufficient_tokens.append((token_contract, chain, data["bars"], min_required_bars))
        
        if insufficient_tokens:
            self.logger.warning(f"Tokens with insufficient data ({len(insufficient_tokens)}) for {data_source.value} {timeframe.value} @ {boundary_ts}:")
            for token_contract, chain, count, required in insufficient_tokens[:10]:
                coverage_pct = (count / required_bars * 100) if required_bars > 0 else 0
                self.logger.warning(
                    f"  - {token_contract[:8]}.../{chain}: {count}/{required_bars} bars ({coverage_pct:.1f}%)"
                )
                # Per-token GT backfill attempt (no longer gated on total bars)
                self._attempt_gt_backfill(token_contract, chain, timeframe, boundary_ts)
            if len(insufficient_tokens) > 10:
                self.logger.warning(f"  ... (+{len(insufficient_tokens) - 10} more tokens)")
        
        if len(bars) < required_bars:
            self.logger.warning(
                f"Partial data for {data_source.value} {timeframe.value} rollup at {boundary_ts}: "
                f"have {len(bars)}/{required_bars} bars ({len(bars)/required_bars*100:.1f}%), proceeding with tolerance"
            )
        
        # Convert to OHLC bars (this already handles per-token processing and 80% tolerance)
        ohlc_bars = self._convert_to_ohlc(bars, timeframe)
        
        if not ohlc_bars:
            self.logger.warning(
                f"No OHLC bars created for {data_source.value} {timeframe.value} rollup at {boundary_ts} "
                f"(had {len(bars)} 1m bars across {len(bars_by_token)} tokens)"
            )
            return 0
        
        # Log conversion summary
        ohlc_by_token = defaultdict(int)
        for bar in ohlc_bars:
            key = (bar.token_contract, bar.chain)
            ohlc_by_token[key] += 1
        
        self.logger.info(
            f"Converted {len(bars)} 1m bars to {len(ohlc_bars)} {timeframe.value} bars "
            f"across {len(ohlc_by_token)} tokens"
        )
        
        # Filter out bars that already exist (per-token check)
        ohlc_bars_to_write = []
        skipped_existing = 0
        skipped_tokens = set()
        created_tokens = set()
        
        for bar in ohlc_bars:
            if self._bar_exists_for_token(data_source, timeframe, boundary_ts, bar.token_contract, bar.chain):
                skipped_existing += 1
                skipped_tokens.add((bar.token_contract, bar.chain))
                self.logger.debug(f"Bar already exists for {bar.token_contract}/{bar.chain} at {boundary_ts}, skipping")
            else:
                ohlc_bars_to_write.append(bar)
                created_tokens.add((bar.token_contract, bar.chain))
        
        if skipped_existing > 0:
            self.logger.info(
                f"Skipped {skipped_existing} existing bars ({len(skipped_tokens)} tokens), "
                f"processing {len(ohlc_bars_to_write)} new bars ({len(created_tokens)} tokens)"
            )
            # Log first 5 skipped tokens
            if skipped_tokens:
                skipped_list = sorted(skipped_tokens)[:5]
                for token_contract, chain in skipped_list:
                    self.logger.info(f"  - Skipped (exists): {token_contract[:8]}.../{chain}")
                if len(skipped_tokens) > 5:
                    self.logger.info(f"  ... (+{len(skipped_tokens) - 5} more tokens)")
        
        if not ohlc_bars_to_write:
            self.logger.info(
                f"All {len(ohlc_bars)} bars already exist for {data_source.value} {timeframe.value} at {boundary_ts} "
                f"({len(skipped_tokens)} tokens)"
            )
            return 0
        
        # Store in database
        written = self._store_ohlc_bars(data_source, ohlc_bars_to_write)
        
        if written > 0:
            # Log which tokens were rolled up
            tokens_rolled = set((bar.token_contract, bar.chain) for bar in ohlc_bars_to_write[:written])
            
            # Calculate per-token bar counts
            bars_by_token_rolled = defaultdict(int)
            for bar in ohlc_bars_to_write[:written]:
                key = (bar.token_contract, bar.chain)
                bars_by_token_rolled[key] += 1
            
            # Log summary
            self.logger.info(
                f"Rolled up {written} {data_source.value} {timeframe.value} bars at {boundary_ts} "
                f"(skipped {skipped_existing} existing, {len(tokens_rolled)} tokens created)"
            )
            
            # Log first 10 tokens with bar counts
            token_list = sorted(tokens_rolled)[:10]
            for token_contract, chain in token_list:
                count = bars_by_token_rolled[(token_contract, chain)]
                self.logger.info(f"  - {token_contract[:8]}.../{chain}: {count} bar(s)")
            if len(tokens_rolled) > 10:
                self.logger.info(f"  ... (+{len(tokens_rolled) - 10} more tokens)")
        else:
            self.logger.warning(
                f"Rollup created {len(ohlc_bars_to_write)} bars but wrote 0 to database for "
                f"{data_source.value} {timeframe.value} at {boundary_ts} ({len(created_tokens)} tokens)"
            )
        
        # Log final summary
        total_tokens_checked = len(bars_by_token)
        tokens_created = len(created_tokens) if written > 0 else 0
        tokens_skipped = len(skipped_tokens)
        tokens_failed = total_tokens_checked - tokens_created - tokens_skipped
        
        self.logger.info(
            f"{timeframe.value} rollup summary at {boundary_ts}: "
            f"{tokens_created} tokens created, {tokens_skipped} tokens skipped (exists), "
            f"{tokens_failed} tokens failed, {total_tokens_checked} total checked"
        )
        
        return written
    
    def _get_majors_1m_data(self, timeframe: Timeframe, boundary_ts: datetime) -> List[Dict]:
        """Get majors 1m data from majors_price_data_ohlc (timeframe='1m') for the timeframe window
        
        Args:
            timeframe: Target timeframe (e.g., M5 for 5m rollup)
            boundary_ts: The boundary timestamp (start of the period being rolled up)
                        For 5m rollup at 12:05:00, boundary_ts = 12:05:00, and we need bars from 12:00:00 to 12:05:00
        """
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        # Look back timeframe_minutes * 2 to ensure we have enough data (like lowcap does)
        # This provides a buffer in case of timing issues or missing bars
        start_time = boundary_ts - timedelta(minutes=timeframe_minutes * 2)
        
        # Read from majors_price_data_ohlc with timeframe='1m'
        # Get bars from start_time up to (but not including) boundary_ts
        result = self.sb.table("majors_price_data_ohlc").select(
            "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume"
        ).eq("chain", "hyperliquid").eq("timeframe", "1m").gte("timestamp", start_time.isoformat()).lt("timestamp", boundary_ts.isoformat()).order("timestamp", desc=False).execute()
        
        self.logger.debug(f"Majors 1m data query: timeframe={timeframe.value}, boundary_ts={boundary_ts}, start_time={start_time}, found {len(result.data or [])} bars")
        
        # Convert to match lowcap format
        converted_data = []
        for bar in (result.data or []):
            converted_data.append({
                'token_contract': bar['token_contract'],
                'chain': bar['chain'],
                'timestamp': bar['timestamp'],
                'open_usd': float(bar['open_usd']),
                'high_usd': float(bar['high_usd']),
                'low_usd': float(bar['low_usd']),
                'close_usd': float(bar['close_usd']),
                'open_native': float(bar['open_native']),
                'high_native': float(bar['high_native']),
                'low_native': float(bar['low_native']),
                'close_native': float(bar['close_native']),
                'volume': float(bar['volume'])
            })
        
        return converted_data
    
    def _get_lowcap_1m_data(self, timeframe: Timeframe, when: datetime, boundary_ts: Optional[datetime] = None) -> List[Dict]:
        """Get lowcap data for the timeframe window"""
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        
        # For 1m timeframe, we need raw price points (not OHLC data)
        if timeframe == Timeframe.M1:
            self.logger.info("Getting 1m price points for 1m OHLC conversion")
            # Fetch a recent slice of raw price points (newest-first) to avoid paging old data.
            # We only need recent minutes to build 1m OHLC; keep it tight (15m window) with a cap.
            window_minutes = 15
            start_time = when - timedelta(minutes=window_minutes)
            row_limit = 1000
            
            result = self.sb.table("lowcap_price_data_1m").select(
                "token_contract,chain,timestamp,price_usd,price_native,volume_5m,volume_1m,volume_1h,volume_6h,volume_24h,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
            ).gte("timestamp", start_time.isoformat()).lt("timestamp", when.isoformat()).order("timestamp", desc=True).limit(row_limit).execute()
            
            price_points_data = result.data or []
            price_points_data.reverse()  # oldest-first for processing
            
            if not price_points_data:
                self.logger.warning(f"No price points returned for 1m conversion (window {start_time} to {when}); latest raw price is stale.")
                return []
            
            # Staleness / truncation checks
            ts_min = datetime.fromisoformat(price_points_data[0]['timestamp'].replace('Z', '+00:00'))
            ts_max = datetime.fromisoformat(price_points_data[-1]['timestamp'].replace('Z', '+00:00'))
            if ts_max < when - timedelta(minutes=5):
                self.logger.warning(
                    f"Stale raw price data for 1m conversion: max_ts={ts_max}, now={when}, age={(when - ts_max).total_seconds()/60:.1f}m"
                )
            if len(price_points_data) == row_limit:
                self.logger.warning(
                    f"Hit row limit ({row_limit}) when fetching price points for 1m conversion (window {start_time} to {when}); data may be truncated"
                )
            
            # Get existing OHLC bars to find which price points are already converted
            table_name = "lowcap_price_data_ohlc"
            existing_ohlc = self.sb.table(table_name).select(
                "token_contract,chain,timestamp"
            ).eq("timeframe", "1m").gte(
                "timestamp", start_time.isoformat()
            ).lt("timestamp", when.isoformat()).execute()
            
            existing_timestamps = set()
            for ohlc in (existing_ohlc.data or []):
                # Round timestamp to minute boundary for comparison
                ts = datetime.fromisoformat(ohlc['timestamp'].replace('Z', '+00:00'))
                ts_minute = ts.replace(second=0, microsecond=0).isoformat()
                key = (ohlc['token_contract'], ohlc['chain'], ts_minute)
                existing_timestamps.add(key)
            
            # Filter out price points that already have OHLC bars
            unprocessed = []
            for point in price_points_data:
                ts = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                ts_minute = ts.replace(second=0, microsecond=0).isoformat()
                key = (point['token_contract'], point['chain'], ts_minute)
                
                if key not in existing_timestamps:
                    unprocessed.append(point)
            
            # Log detailed breakdown
            points_by_token = defaultdict(int)
            timestamp_range = {"min": None, "max": None}
            for point in unprocessed:
                key = (point['token_contract'], point['chain'])
                points_by_token[key] += 1
                ts = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                if timestamp_range["min"] is None or ts < timestamp_range["min"]:
                    timestamp_range["min"] = ts
                if timestamp_range["max"] is None or ts > timestamp_range["max"]:
                    timestamp_range["max"] = ts
            
            self.logger.info(
                f"Found {len(unprocessed)} unprocessed price points out of {len(price_points_data)} total "
                f"across {len(points_by_token)} tokens (range: {timestamp_range['min']} to {timestamp_range['max']})"
            )
            
            # Log per-token breakdown (first 10 tokens)
            if points_by_token:
                token_list = sorted(points_by_token.items())[:10]
                for (token_contract, chain), count in token_list:
                    self.logger.info(f"  - {token_contract[:8]}.../{chain}: {count} unprocessed points")
                if len(points_by_token) > 10:
                    self.logger.info(f"  ... (+{len(points_by_token) - 10} more tokens)")
            
            return unprocessed
        
        # For higher timeframes, prioritize existing OHLC data (15m) for rollup
        # because 15m data has proper OHLC format and covers more history
        
        # Use boundary_ts if provided (for consistency with majors), otherwise use when
        end_time = boundary_ts if boundary_ts else when
        
        # First try 1m OHLC data from OHLC table (preferred for rollup)
        start_time = end_time - timedelta(minutes=timeframe_minutes * 2)
        self.logger.info(
            f"Trying 1m OHLC data first for {timeframe.value} rollup "
            f"(window: {start_time} to {end_time}, {timeframe_minutes * 2} minutes)"
        )
        
        # Use pagination to get all records (Supabase has 1000 record limit)
        all_data = []
        page_size = 1000
        offset = 0
        
        while True:
            result = self.sb.table("lowcap_price_data_ohlc").select(
                "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
            ).eq("timeframe", "1m").gte("timestamp", start_time.isoformat()).lt("timestamp", end_time.isoformat()).order("timestamp", desc=False).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
                
            all_data.extend(result.data)
            
            # If we got less than page_size, we've reached the end
            if len(result.data) < page_size:
                break
                
            offset += page_size
        
        if all_data:
            # Log what we found
            data_by_token = defaultdict(int)
            for bar in all_data:
                key = (bar['token_contract'], bar['chain'])
                data_by_token[key] += 1
            
            self.logger.info(
                f"Found {len(all_data)} 1m OHLC bars across {len(data_by_token)} tokens "
                f"for {timeframe.value} rollup (window: {start_time} to {end_time})"
            )
            
            # For timeframes that need volume from price points (5m, 1h, 4h, 1d),
            # we need to also get the price points to access volume_1h, volume_6h, etc.
            if timeframe in [Timeframe.M5, Timeframe.H1, Timeframe.H4, Timeframe.D1]:
                # Get price points for the same period to access volume data
                price_points_result = self.sb.table("lowcap_price_data_1m").select(
                    "token_contract,chain,timestamp,volume_5m,volume_1h,volume_6h,volume_24h,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
                ).gte(
                    "timestamp", start_time.isoformat()
                ).lt("timestamp", end_time.isoformat()).order(
                    "timestamp", desc=False
                ).execute()
                
                # Create a lookup map: (token, chain, minute) -> volume data
                volume_lookup = {}
                for point in (price_points_result.data or []):
                    ts = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                    minute_key = ts.replace(second=0, microsecond=0)
                    key = (point['token_contract'], point['chain'], minute_key.isoformat())
                    volume_lookup[key] = point
                
                # Add volume data to OHLC bars
                for bar in all_data:
                    bar_key = (bar['token_contract'], bar['chain'], bar['timestamp'])
                    if bar_key in volume_lookup:
                        point = volume_lookup[bar_key]
                        bar['volume_5m'] = point.get('volume_5m', 0)  # m5 volume
                        bar['volume_1h'] = point.get('volume_1h', 0)
                        bar['volume_6h'] = point.get('volume_6h', 0)
                        bar['volume_24h'] = point.get('volume_24h', 0)
            
            return all_data
        
        # Fallback to 15m OHLC data if no 1m OHLC data available
        self.logger.warning(
            f"No 1m OHLC data found for {timeframe.value} rollup (window: {start_time} to {end_time}), "
            f"trying 15m OHLC data as fallback"
        )
        all_data = []
        offset = 0
        
        while True:
            result = self.sb.table("lowcap_price_data_ohlc").select(
                "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
            ).eq("timeframe", "15m").gte("timestamp", start_time.isoformat()).lt("timestamp", end_time.isoformat()).order("timestamp", desc=False).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
                
            all_data.extend(result.data)
            
            if len(result.data) < page_size:
                break
                
            offset += page_size
        
        if all_data:
            data_by_token = defaultdict(int)
            for bar in all_data:
                key = (bar['token_contract'], bar['chain'])
                data_by_token[key] += 1
            
            self.logger.info(
                f"Found {len(all_data)} 15m OHLC bars across {len(data_by_token)} tokens "
                f"for {timeframe.value} rollup (fallback, window: {start_time} to {end_time})"
            )
            return all_data
        
        # Final fallback to raw 1m price points
        self.logger.warning(
            f"No OHLC data found for {timeframe.value} rollup (window: {start_time} to {end_time}), "
            f"falling back to raw 1m price points"
        )
        result = self.sb.table("lowcap_price_data_1m").select(
            "token_contract,chain,timestamp,price_usd,price_native,volume_1m,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
        ).gte("timestamp", start_time.isoformat()).lt("timestamp", end_time.isoformat()).order("timestamp", desc=False).execute()
        
        price_points = result.data or []
        if price_points:
            points_by_token = defaultdict(int)
            for point in price_points:
                key = (point['token_contract'], point['chain'])
                points_by_token[key] += 1
            
            self.logger.info(
                f"Found {len(price_points)} raw 1m price points across {len(points_by_token)} tokens "
                f"for {timeframe.value} rollup (fallback, window: {start_time} to {end_time})"
            )
        
        return price_points
    
    def _get_tokens_with_1m_data(
        self, 
        data_source: DataSource, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Tuple[str, str]]:
        """Get list of (token_contract, chain) tuples that have 1m data in the time range"""
        try:
            if data_source == DataSource.MAJORS:
                # For majors, check majors_price_data_ohlc (timeframe='1m')
                result = self.sb.table("majors_price_data_ohlc").select(
                    "token_contract,chain"
                ).eq("timeframe", "1m").gte(
                    "timestamp", start_time.isoformat()
                ).lt("timestamp", end_time.isoformat()).execute()
            else:
                # For lowcaps, check lowcap_price_data_ohlc (timeframe='1m')
                result = self.sb.table("lowcap_price_data_ohlc").select(
                    "token_contract,chain"
                ).eq("timeframe", "1m").gte(
                    "timestamp", start_time.isoformat()
                ).lt("timestamp", end_time.isoformat()).execute()
            
            # Get unique (token_contract, chain) pairs
            tokens = set()
            for row in (result.data or []):
                tokens.add((row['token_contract'], row['chain']))
            
            return list(tokens)
        except Exception as e:
            self.logger.error(f"Error getting tokens with 1m data: {e}", exc_info=True)
            return []
    
    def _get_existing_boundaries(
        self,
        data_source: DataSource,
        timeframe: Timeframe,
        tokens: List[Tuple[str, str]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[Tuple[str, str], set]:
        """Get existing boundaries for tokens in time range
        
        Returns:
            Dict mapping (token_contract, chain) -> set of boundary timestamps (ISO strings)
        """
        try:
            table_name = "majors_price_data_ohlc" if data_source == DataSource.MAJORS else "lowcap_price_data_ohlc"
            
            # Build query for all tokens at once (more efficient)
            query = self.sb.table(table_name).select(
                "token_contract,chain,timestamp"
            ).eq("timeframe", timeframe.value).gte(
                "timestamp", start_time.isoformat()
            ).lt("timestamp", end_time.isoformat())
            
            # Execute query
            result = query.execute()
            
            # Group by (token_contract, chain)
            existing = defaultdict(set)
            for row in (result.data or []):
                key = (row['token_contract'], row['chain'])
                if key in tokens:  # Only include requested tokens
                    existing[key].add(row['timestamp'])
            
            return dict(existing)
        except Exception as e:
            self.logger.error(f"Error getting existing boundaries: {e}", exc_info=True)
            return {}
    
    def _generate_expected_boundaries(
        self,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime
    ) -> List[datetime]:
        """Generate list of expected boundary timestamps for a timeframe"""
        boundaries = []
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        
        # Start from first boundary at or after start_time
        current = self._get_timeframe_boundary_ts(start_time, timeframe)
        if current < start_time:
            # Move to next boundary by adding timeframe_minutes
            current = current + timedelta(minutes=timeframe_minutes)
            # Recalculate boundary to ensure correct alignment
            current = self._get_timeframe_boundary_ts(current, timeframe)
        
        # Generate boundaries up to end_time
        while current < end_time:
            boundaries.append(current)
            # Move to next boundary
            current = current + timedelta(minutes=timeframe_minutes)
            # For timeframes that need special alignment (4h, 1d), recalculate
            # For others (5m, 15m, 1h), the simple addition should work
            if timeframe in [Timeframe.H4, Timeframe.D1]:
                current = self._get_timeframe_boundary_ts(current, timeframe)
        
        return boundaries
    
    def catch_up_rollups(
        self,
        data_source: DataSource,
        timeframe: Timeframe,
        lookback_hours: int = 24,
        max_boundaries: int = 100,
        max_tokens: int = 50,
        tokens: Optional[List[Tuple[str, str]]] = None
    ) -> Dict[str, Any]:
        """Catch up on missed rollup boundaries
        
        Args:
            data_source: MAJORS or LOWCAPS
            timeframe: Target timeframe (5m, 15m, 1h, 4h)
            lookback_hours: How many hours back to check (default: 24)
            max_boundaries: Maximum boundaries to process per run (default: 100)
            max_tokens: Maximum tokens to process per run (default: 50)
            tokens: Optional list of (token_contract, chain) tuples to process.
                   If None, processes all tokens with 1m data in lookback period.
        
        Returns:
            Dict with summary of catch-up operation
        """
        end_time = datetime.now(tz=timezone.utc)
        start_time = end_time - timedelta(hours=lookback_hours)
        
        self.logger.info(
            f"Starting catch-up for {data_source.value} {timeframe.value} "
            f"(lookback: {lookback_hours}h, max_boundaries: {max_boundaries}, max_tokens: {max_tokens})"
        )
        
        # Get tokens to process
        if tokens is None:
            tokens = self._get_tokens_with_1m_data(data_source, start_time, end_time)
            self.logger.info(f"Found {len(tokens)} tokens with 1m data in lookback period")
        
        if not tokens:
            return {
                "status": "no_tokens",
                "tokens_processed": 0,
                "boundaries_filled": 0,
                "boundaries_skipped": 0,
                "errors": []
            }
        
        # Limit tokens
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
            self.logger.info(f"Limited to {max_tokens} tokens (had {len(tokens) + max_tokens - len(tokens)})")
        
        # Get existing boundaries for all tokens (batch query)
        existing_boundaries = self._get_existing_boundaries(
            data_source, timeframe, tokens, start_time, end_time
        )
        
        # Generate expected boundaries
        expected_boundaries = self._generate_expected_boundaries(timeframe, start_time, end_time)
        
        # Find missing boundaries per token
        missing_by_token = {}
        for token_key in tokens:
            existing = existing_boundaries.get(token_key, set())
            missing = []
            for boundary_ts in expected_boundaries:
                boundary_iso = boundary_ts.isoformat()
                if boundary_iso not in existing:
                    missing.append(boundary_ts)
            if missing:
                missing_by_token[token_key] = missing
        
        total_missing = sum(len(missing) for missing in missing_by_token.values())
        self.logger.info(f"Found {total_missing} missing boundaries across {len(missing_by_token)} tokens")
        
        if not missing_by_token:
            return {
                "status": "no_gaps",
                "tokens_processed": len(tokens),
                "boundaries_filled": 0,
                "boundaries_skipped": 0,
                "errors": []
            }
        
        # Process boundaries in batches
        boundaries_filled = 0
        boundaries_skipped = 0
        errors = []
        processed_count = 0
        
        # Flatten missing boundaries with token info, sort by timestamp (oldest first)
        all_missing = []
        for token_key, missing_list in missing_by_token.items():
            for boundary_ts in missing_list:
                all_missing.append((token_key, boundary_ts))
        all_missing.sort(key=lambda x: x[1])  # Sort by timestamp
        
        # Limit total boundaries to process
        if len(all_missing) > max_boundaries:
            all_missing = all_missing[:max_boundaries]
            self.logger.info(f"Limited to {max_boundaries} boundaries (had {len(all_missing) + max_boundaries - len(all_missing)})")
        
        # Process each missing boundary
        for token_key, boundary_ts in all_missing:
            try:
                token_contract, chain = token_key
                
                # Use existing rollup_timeframe method with the boundary timestamp
                written = self.rollup_timeframe(
                    data_source=data_source,
                    timeframe=timeframe,
                    when=boundary_ts
                )
                
                if written > 0:
                    boundaries_filled += 1
                else:
                    boundaries_skipped += 1
                
                processed_count += 1
                
            except Exception as e:
                error_msg = f"{token_key[0][:8]}.../{token_key[1]} at {boundary_ts}: {e}"
                self.logger.error(f"Catch-up error: {error_msg}", exc_info=True)
                errors.append(error_msg)
        
        self.logger.info(
            f"Catch-up complete: {boundaries_filled} filled, {boundaries_skipped} skipped, "
            f"{len(errors)} errors out of {processed_count} processed"
        )
        
        return {
            "status": "complete",
            "tokens_processed": len(missing_by_token),
            "boundaries_filled": boundaries_filled,
            "boundaries_skipped": boundaries_skipped,
            "total_missing": total_missing,
            "errors": errors
        }
    
    def _get_timeframe_minutes(self, timeframe: Timeframe) -> int:
        """Get number of minutes for a timeframe"""
        timeframe_map = {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440
        }
        return timeframe_map[timeframe]
    
    def _get_required_bars_count(self, timeframe: Timeframe) -> int:
        """Get the number of 1m bars required for a timeframe"""
        return self._get_timeframe_minutes(timeframe)
    
    def _is_at_timeframe_boundary(self, when: datetime, timeframe: Timeframe) -> bool:
        """Check if we're at a timeframe boundary"""
        if timeframe == Timeframe.M15:
            # 15m boundaries: :00, :15, :30, :45
            return when.minute % 15 == 0 and when.second < 60
        elif timeframe == Timeframe.H1:
            # 1h boundaries: :00
            return when.minute == 0 and when.second < 60
        elif timeframe == Timeframe.H4:
            # 4h boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
            return when.hour % 4 == 0 and when.minute == 0 and when.second < 60
        elif timeframe == Timeframe.D1:
            # 1d boundaries: 00:00
            return when.hour == 0 and when.minute == 0 and when.second < 60
        elif timeframe == Timeframe.M5:
            # 5m boundaries: :00, :05, :10, :15, etc.
            return when.minute % 5 == 0 and when.second < 60
        else:
            return False
    
    def _get_timeframe_boundary_ts(self, when: datetime, timeframe: Timeframe) -> datetime:
        """Get the timeframe boundary timestamp for a given time"""
        return self._get_timeframe_boundary(when, self._get_timeframe_minutes(timeframe))
    
    def _get_timeframe_boundary(self, ts: datetime, timeframe_minutes: int) -> datetime:
        """Calculate timeframe boundary for a timestamp"""
        if timeframe_minutes == 5:
            # 5m boundaries: :00, :05, :10, :15, etc.
            minute_boundary = (ts.minute // 5) * 5
            return ts.replace(minute=minute_boundary, second=0, microsecond=0)
        elif timeframe_minutes == 15:
            # 15m boundaries: :00, :15, :30, :45
            minute_boundary = (ts.minute // 15) * 15
            return ts.replace(minute=minute_boundary, second=0, microsecond=0)
        elif timeframe_minutes == 60:
            # 1h boundaries: :00
            return ts.replace(minute=0, second=0, microsecond=0)
        elif timeframe_minutes == 240:
            # 4h boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
            hour_boundary = (ts.hour // 4) * 4
            return ts.replace(hour=hour_boundary, minute=0, second=0, microsecond=0)
        elif timeframe_minutes == 1440:
            # 1d boundaries: 00:00
            return ts.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Generic: round down to nearest timeframe_minutes
            total_minutes = ts.hour * 60 + ts.minute
            boundary_minutes = (total_minutes // timeframe_minutes) * timeframe_minutes
            boundary_hour = boundary_minutes // 60
            boundary_minute = boundary_minutes % 60
            return ts.replace(hour=boundary_hour, minute=boundary_minute, second=0, microsecond=0)
    
    def _bar_exists(self, data_source: DataSource, timeframe: Timeframe, boundary_ts: datetime) -> bool:
        """Check if ANY rollup bar already exists for this timeframe and boundary (legacy method, use _bar_exists_for_token)"""
        try:
            table_name = "majors_price_data_ohlc" if data_source == DataSource.MAJORS else "lowcap_price_data_ohlc"
            
            # Check if any bar exists for any token at this boundary
            result = self.sb.table(table_name).select(
                "token_contract"
            ).eq("timeframe", timeframe.value).eq(
                "timestamp", boundary_ts.isoformat()
            ).limit(1).execute()
            
            exists = len(result.data or []) > 0
            if exists:
                self.logger.debug(f"Bar exists check: {table_name} {timeframe.value} {boundary_ts} -> EXISTS")
            return exists
        except Exception as e:
            self.logger.error(f"Error checking if bar exists for {data_source.value} {timeframe.value} at {boundary_ts}: {e}", exc_info=True)
            return False
    
    def _bar_exists_for_token(self, data_source: DataSource, timeframe: Timeframe, boundary_ts: datetime, token_contract: str, chain: str) -> bool:
        """Check if a rollup bar already exists for a specific token at this timeframe and boundary"""
        try:
            table_name = "majors_price_data_ohlc" if data_source == DataSource.MAJORS else "lowcap_price_data_ohlc"
            
            # Check if bar exists for this specific token
            result = self.sb.table(table_name).select(
                "token_contract"
            ).eq("timeframe", timeframe.value).eq(
                "timestamp", boundary_ts.isoformat()
            ).eq("token_contract", token_contract).eq("chain", chain).limit(1).execute()
            
            return len(result.data or []) > 0
        except Exception as e:
            self.logger.error(f"Error checking if bar exists for {token_contract}/{chain} {timeframe.value} at {boundary_ts}: {e}", exc_info=True)
            return False  # On error, assume doesn't exist so we try to write it
    
    def _convert_to_ohlc(self, bars: List[Dict], timeframe: Timeframe) -> List[OHLCBar]:
        """Convert 1m data to OHLC bars for the timeframe"""
        if not bars:
            return []
        
        # Special handling for 1m timeframe: convert price points to 1m OHLC bars
        if timeframe == Timeframe.M1:
            return self._convert_1m_to_ohlc(bars)
        
        # For higher timeframes, use standard rollup logic
        # Group bars by token_contract and chain
        grouped_bars = {}
        for bar in bars:
            key = (bar['token_contract'], bar['chain'])
            if key not in grouped_bars:
                grouped_bars[key] = []
            grouped_bars[key].append(bar)
        
        ohlc_bars = []
        
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        
        for (token_contract, chain), token_bars in grouped_bars.items():
            # Sort by timestamp
            token_bars.sort(key=lambda x: x['timestamp'])
            
            if not token_bars:
                continue
            
            # Group by timeframe boundary
            timeframe_bars = defaultdict(list)
            
            for bar in token_bars:
                # Parse timestamp and group by timeframe boundary
                ts = datetime.fromisoformat(bar['timestamp'].replace('Z', '+00:00'))
                
                # Calculate timeframe boundary based on timeframe_minutes
                if timeframe_minutes == 5:
                    # 5m boundaries: :00, :05, :10, :15, etc.
                    minute_boundary = (ts.minute // 5) * 5
                    timeframe_key = ts.replace(minute=minute_boundary, second=0, microsecond=0)
                elif timeframe_minutes == 15:
                    # 15m boundaries: :00, :15, :30, :45
                    minute_boundary = (ts.minute // 15) * 15
                    timeframe_key = ts.replace(minute=minute_boundary, second=0, microsecond=0)
                elif timeframe_minutes == 60:
                    # 1h boundaries: :00
                    timeframe_key = ts.replace(minute=0, second=0, microsecond=0)
                elif timeframe_minutes == 240:
                    # 4h boundaries: :00, :04, :08, :12, :16, :20
                    hour_boundary = (ts.hour // 4) * 4
                    timeframe_key = ts.replace(hour=hour_boundary, minute=0, second=0, microsecond=0)
                elif timeframe_minutes == 1440:
                    # 1d boundaries: 00:00
                    timeframe_key = ts.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    # Generic: round down to nearest timeframe_minutes
                    total_minutes = ts.hour * 60 + ts.minute
                    boundary_minutes = (total_minutes // timeframe_minutes) * timeframe_minutes
                    boundary_hour = boundary_minutes // 60
                    boundary_minute = boundary_minutes % 60
                    timeframe_key = ts.replace(hour=boundary_hour, minute=boundary_minute, second=0, microsecond=0)
                
                timeframe_bars[timeframe_key].append(bar)
            
            # Create OHLC bars for each timeframe period
            for timeframe_ts, period_bars in timeframe_bars.items():
                if not period_bars:
                    continue
                
                # Validate with dynamic threshold based on collection interval
                coverage_threshold = self._get_dynamic_coverage_threshold()
                min_required_bars = max(1, int(timeframe_minutes * coverage_threshold))
                partial = False
                coverage_pct = (len(period_bars) / timeframe_minutes * 100) if timeframe_minutes > 0 else 0
                if len(period_bars) < min_required_bars:
                    partial = True
                    self.logger.info(
                        f"Creating PARTIAL {timeframe.value} bar at {timeframe_ts} for {token_contract[:8]}.../{chain}: "
                        f"{len(period_bars)}/{timeframe_minutes} 1m bars ({coverage_pct:.1f}% coverage, "
                        f"need at least {min_required_bars} for {timeframe_minutes}min timeframe)"
                    )
                bars_used = len(period_bars)
                expected_bars = timeframe_minutes
                    
                # Sort by timestamp to get proper OHLC
                period_bars.sort(key=lambda x: x['timestamp'])
                
                # Check if we have OHLC data (from 1m OHLC or 15m backfill) or price points (from 1m data)
                has_ohlc_data = 'open_usd' in period_bars[0]
                def _sum_period_volume():
                    return sum(float(bar.get('volume', 0) or 0) for bar in period_bars)
                
                if has_ohlc_data:
                    # Calculate OHLC from actual OHLC data (rollup from 1m OHLC bars)
                    # Using USD prices only (native prices stay 0.0)
                    open_price_usd = float(period_bars[0]['open_usd'])
                    close_price_usd = float(period_bars[-1]['close_usd'])
                    high_price_usd = max(float(bar['high_usd']) for bar in period_bars)
                    low_price_usd = min(float(bar['low_usd']) for bar in period_bars)
                    
                    open_price_native = float(period_bars[0].get('open_native', 0) or 0)
                    close_price_native = float(period_bars[-1].get('close_native', 0) or 0)
                    high_price_native = max(float(bar.get('high_native', 0) or 0) for bar in period_bars)
                    low_price_native = min(float(bar.get('low_native', 0) or 0) for bar in period_bars)
                    
                    # Volume depends on timeframe:
                    # - 5m: use m5 directly from latest bar in period (from price point)
                    # - 15m: sum of 1m volumes
                    # - 1h: use h1 directly from latest bar in period (from price point)
                    # - 4h: use h6 * 4/6 from latest bar in period (from price point)
                    # - 1d: use h24 directly from latest bar in period (from price point)
                    latest_bar = period_bars[-1]
                    metadata = self._extract_metadata(latest_bar)
                    if timeframe == Timeframe.M5:
                        volume = float(latest_bar.get('volume_5m', 0) or 0)
                        if volume == 0:
                            volume = _sum_period_volume()
                    elif timeframe == Timeframe.M15:
                        volume = _sum_period_volume()
                    elif timeframe == Timeframe.H1:
                        volume = float(latest_bar.get('volume_1h', 0) or 0)
                        if volume == 0:
                            volume = _sum_period_volume()
                    elif timeframe == Timeframe.H4:
                        volume_6h = float(latest_bar.get('volume_6h', 0) or 0)
                        if volume_6h > 0:
                            volume = volume_6h * (4.0 / 6.0)
                        else:
                            volume = _sum_period_volume()
                    elif timeframe == Timeframe.D1:
                        volume = float(latest_bar.get('volume_24h', 0) or 0)
                        if volume == 0:
                            volume = _sum_period_volume()
                    else:
                        volume = _sum_period_volume()
                else:
                    # Calculate OHLC from price points (fallback - should not happen if 1m OHLC exists)
                    prices_usd = [float(bar['price_usd']) for bar in period_bars]
                    prices_native = [float(bar.get('price_native', 0) or 0) for bar in period_bars]
                    
                    open_price_usd = prices_usd[0]
                    close_price_usd = prices_usd[-1]
                    high_price_usd = max(prices_usd)
                    low_price_usd = min(prices_usd)
                    
                    open_price_native = prices_native[0]
                    close_price_native = prices_native[-1]
                    high_price_native = max(prices_native)
                    low_price_native = min(prices_native)
                    
                    # Volume depends on timeframe (same logic as above)
                    latest_bar = period_bars[-1]
                    metadata = self._extract_metadata(latest_bar)
                    if timeframe == Timeframe.M5:
                        volume = float(latest_bar.get('volume_5m', 0) or 0)
                        if volume == 0:
                            volume = _sum_period_volume()
                    elif timeframe == Timeframe.M15:
                        volume = _sum_period_volume()
                    elif timeframe == Timeframe.H1:
                        volume = float(latest_bar.get('volume_1h', 0) or 0)
                        if volume == 0:
                            volume = _sum_period_volume()
                    elif timeframe == Timeframe.H4:
                        volume_6h = float(latest_bar.get('volume_6h', 0) or 0)
                        if volume_6h > 0:
                            volume = volume_6h * (4.0 / 6.0)
                        else:
                            volume = _sum_period_volume()
                    elif timeframe == Timeframe.D1:
                        volume = float(latest_bar.get('volume_24h', 0) or 0)
                        if volume == 0:
                            volume = _sum_period_volume()
                    else:
                        volume = _sum_period_volume()
                
                # Create OHLC bar
                ohlc_bar = OHLCBar(
                    token_contract=token_contract,
                    chain=chain,
                    timeframe=timeframe.value,
                    timestamp=timeframe_ts,
                    open_native=open_price_native,
                    high_native=high_price_native,
                    low_native=low_price_native,
                    close_native=close_price_native,
                    open_usd=open_price_usd,
                    high_usd=high_price_usd,
                    low_usd=low_price_usd,
                    close_usd=close_price_usd,
                    volume=volume,
                    source="partial" if partial else "rollup",
                    partial=partial,
                    coverage_pct=coverage_pct,
                    bars_used=bars_used,
                    expected_bars=expected_bars,
                    **metadata
                )
                ohlc_bars.append(ohlc_bar)
                coverage_pct = (len(period_bars) / timeframe_minutes * 100) if timeframe_minutes > 0 else 0
                self.logger.debug(
                    f"Created {timeframe.value} bar for {token_contract[:8]}.../{chain} at {timeframe_ts}: "
                    f"{len(period_bars)}/{timeframe_minutes} bars ({coverage_pct:.1f}% coverage)"
                )
        
        return ohlc_bars
    
    def _convert_1m_to_ohlc(self, bars: List[Dict]) -> List[OHLCBar]:
        """
        Convert 1m price points to 1m OHLC bars (CRITICAL - different from rollup).
        
        Logic:
        - Open = Previous candle's close (or first price if no previous)
        - Close = Last price in minute
        - High = max of all prices in minute (including open if it's from previous)
        - Low = min of all prices in minute (including open if it's from previous)
        - Volume = sum of volume_1m for all price points in minute
        
        This is creating OHLC from price points, not rolling up to higher timeframe.
        """
        if not bars:
            return []
        
        # Group bars by token_contract and chain
        grouped_bars = defaultdict(list)
        for bar in bars:
            key = (bar['token_contract'], bar['chain'])
            grouped_bars[key].append(bar)
        
        ohlc_bars = []
        
        for (token_contract, chain), token_bars in grouped_bars.items():
            # Sort by timestamp
            token_bars.sort(key=lambda x: x['timestamp'])
            
            if not token_bars:
                continue
            
            # Group price points by minute boundary (handle edge case of multiple points per minute)
            minute_groups = defaultdict(list)
            
            for bar in token_bars:
                ts = datetime.fromisoformat(bar['timestamp'].replace('Z', '+00:00'))
                minute_key = ts.replace(second=0, microsecond=0)
                minute_groups[minute_key].append(bar)
            
            # Get previous close from the last processed minute (for continuity)
            previous_close_usd = None
            previous_close_native = None
            
            # Process each minute group
            for minute_ts in sorted(minute_groups.keys()):
                minute_bars = minute_groups[minute_ts]
                
                # If multiple price points in same minute, aggregate them
                prices_usd = [float(b['price_usd']) for b in minute_bars]
                prices_native = [float(b['price_native']) for b in minute_bars]
                
                # Open = first price in minute (or previous close if available)
                if previous_close_usd is not None:
                    open_price_usd = previous_close_usd
                    open_price_native = previous_close_native
                else:
                    open_price_usd = prices_usd[0]
                    open_price_native = prices_native[0]
                
                # Close = last price in minute
                close_price_usd = prices_usd[-1]
                close_price_native = prices_native[-1]
                
                # High = max of all prices in minute (including open if it's from previous)
                high_price_usd = max([open_price_usd] + prices_usd)
                low_price_usd = min([open_price_usd] + prices_usd)
                high_price_native = max([open_price_native] + prices_native)
                low_price_native = min([open_price_native] + prices_native)
                
                # Volume for 1m OHLC: use volume_1m (m5/5)
                volume_1m_values = [float(b.get('volume_1m', 0) or 0) for b in minute_bars]
                if any(volume_1m_values):
                    volume = sum(volume_1m_values)
                else:
                    # Fallback: calculate from m5 if volume_1m not available
                    volumes_5m = [float(b.get('volume_5m', 0) or 0) for b in minute_bars]
                    volume = sum(volumes_5m) / 5.0 if volumes_5m else 0
                
                latest_point = minute_bars[-1]
                liquidity_usd = float(latest_point.get('liquidity_usd', 0) or 0)
                liquidity_change_1m = float(latest_point.get('liquidity_change_1m', 0) or 0)
                price_change_24h = float(latest_point.get('price_change_24h', 0) or 0)
                market_cap = float(latest_point.get('market_cap', 0) or 0)
                fdv = float(latest_point.get('fdv', 0) or 0)
                dex_id = latest_point.get('dex_id')
                pair_address = latest_point.get('pair_address')
                
                # Create OHLC bar for this minute
                ohlc_bar = OHLCBar(
                    token_contract=token_contract,
                    chain=chain,
                    timeframe="1m",
                    timestamp=minute_ts,
                    open_native=open_price_native,
                    high_native=high_price_native,
                    low_native=low_price_native,
                    close_native=close_price_native,
                    open_usd=open_price_usd,
                    high_usd=high_price_usd,
                    low_usd=low_price_usd,
                    close_usd=close_price_usd,
                    volume=volume,
                    liquidity_usd=liquidity_usd,
                    liquidity_change_1m=liquidity_change_1m,
                    price_change_24h=price_change_24h,
                    market_cap=market_cap,
                    fdv=fdv,
                    dex_id=dex_id,
                    pair_address=pair_address,
                    source="1m_conversion",
                    partial=False,
                    coverage_pct=100.0,
                    bars_used=len(minute_bars),
                    expected_bars=1
                )
                ohlc_bars.append(ohlc_bar)
                
                # Update previous close for next iteration
                previous_close_usd = close_price_usd
                previous_close_native = close_price_native
        
        return ohlc_bars
    
    def _extract_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata fields for OHLC storage"""
        return {
            "liquidity_usd": float(record.get('liquidity_usd', 0) or 0),
            "liquidity_change_1m": float(record.get('liquidity_change_1m', 0) or 0),
            "price_change_24h": float(record.get('price_change_24h', 0) or 0),
            "market_cap": float(record.get('market_cap', 0) or 0),
            "fdv": float(record.get('fdv', 0) or 0),
            "dex_id": record.get('dex_id'),
            "pair_address": record.get('pair_address')
        }
    
    def _validate_ohlc_bar(self, bar: OHLCBar) -> tuple[bool, Optional[str]]:
        """Validate an OHLC bar for data quality issues
        
        Returns:
            (is_valid, error_message)
        """
        # Check prices are positive
        if bar.open_usd <= 0 or bar.close_usd <= 0 or bar.high_usd <= 0 or bar.low_usd <= 0:
            return False, f"Non-positive USD prices: O={bar.open_usd}, H={bar.high_usd}, L={bar.low_usd}, C={bar.close_usd}"
        
        # Check high >= low
        if bar.high_usd < bar.low_usd:
            return False, f"High < Low: H={bar.high_usd}, L={bar.low_usd}"
        
        # Check prices are within reasonable range (not NaN, not infinity)
        import math
        for price in [bar.open_usd, bar.high_usd, bar.low_usd, bar.close_usd]:
            if math.isnan(price) or math.isinf(price):
                return False, f"Invalid price value: {price}"
        
        # Check high >= open and high >= close
        if bar.high_usd < bar.open_usd or bar.high_usd < bar.close_usd:
            return False, f"High < Open or Close: H={bar.high_usd}, O={bar.open_usd}, C={bar.close_usd}"
        
        # Check low <= open and low <= close
        if bar.low_usd > bar.open_usd or bar.low_usd > bar.close_usd:
            return False, f"Low > Open or Close: L={bar.low_usd}, O={bar.open_usd}, C={bar.close_usd}"
        
        # Check volume is non-negative
        if bar.volume < 0:
            return False, f"Negative volume: {bar.volume}"
        
        # Check native prices if they're set (should be >= 0)
        if bar.open_native < 0 or bar.high_native < 0 or bar.low_native < 0 or bar.close_native < 0:
            return False, f"Negative native prices: O={bar.open_native}, H={bar.high_native}, L={bar.low_native}, C={bar.close_native}"
        
        return True, None
    
    def _store_ohlc_bars(self, data_source: DataSource, bars: List[OHLCBar]) -> int:
        """Store OHLC bars in the appropriate table"""
        if not bars:
            return 0
        
        # Validate and filter bars
        valid_bars = []
        invalid_count = 0
        for bar in bars:
            is_valid, error_msg = self._validate_ohlc_bar(bar)
            if is_valid:
                valid_bars.append(bar)
            else:
                invalid_count += 1
                self.logger.warning(
                    f"Invalid OHLC bar rejected for {bar.token_contract}/{bar.chain} "
                    f"at {bar.timestamp} ({bar.timeframe}): {error_msg}"
                )
        
        if invalid_count > 0:
            self.logger.warning(f"Rejected {invalid_count} invalid bars out of {len(bars)} total")
        
        if not valid_bars:
            self.logger.error("No valid bars to store after validation")
            return 0
        
        # Convert OHLCBar objects to database rows
        rows = []
        for bar in valid_bars:
            row = {
                "token_contract": bar.token_contract,
                "chain": bar.chain,
                "timeframe": bar.timeframe,
                "timestamp": bar.timestamp.isoformat(),
                "open_native": bar.open_native,
                "high_native": bar.high_native,
                "low_native": bar.low_native,
                "close_native": bar.close_native,
                "open_usd": bar.open_usd,
                "high_usd": bar.high_usd,
                "low_usd": bar.low_usd,
                "close_usd": bar.close_usd,
                "volume": bar.volume,
                "source": bar.source,
                "partial": bar.partial,
                "coverage_pct": bar.coverage_pct,
                "bars_used": bar.bars_used,
                "expected_bars": bar.expected_bars
            }
            if data_source == DataSource.LOWCAPS:
                row.update({
                    "liquidity_usd": bar.liquidity_usd,
                    "liquidity_change_1m": bar.liquidity_change_1m,
                    "price_change_24h": bar.price_change_24h,
                    "market_cap": bar.market_cap,
                    "fdv": bar.fdv,
                    "dex_id": bar.dex_id,
                    "pair_address": bar.pair_address,
                })
            rows.append(row)
        
        # Store in appropriate table
        if data_source == DataSource.MAJORS:
            table_name = "majors_price_data_ohlc"
        else:
            table_name = "lowcap_price_data_ohlc"
        
        try:
            result = self.sb.table(table_name).upsert(
                rows, 
                on_conflict="token_contract,chain,timeframe,timestamp"
            ).execute()
            
            self.logger.info(f"Stored {len(rows)} bars in {table_name}")
            return len(rows)
            
        except Exception as e:
            self.logger.error(f"Error storing OHLC bars: {e}")
            return 0


def main():
    """Main entry point for testing"""
    import sys
    
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    rollup = GenericOHLCRollup()
    
    # Check if catch-up command
    if len(sys.argv) > 1 and sys.argv[1] == "catch-up":
        # Usage: python rollup_ohlc.py catch-up [data_source] [timeframe] [lookback_hours] [max_boundaries] [max_tokens]
        # Example: python rollup_ohlc.py catch-up lowcaps 15m 24 100 50
        data_source_str = sys.argv[2] if len(sys.argv) > 2 else "lowcaps"
        timeframe_str = sys.argv[3] if len(sys.argv) > 3 else "15m"
        lookback_hours = int(sys.argv[4]) if len(sys.argv) > 4 else 24
        max_boundaries = int(sys.argv[5]) if len(sys.argv) > 5 else 100
        max_tokens = int(sys.argv[6]) if len(sys.argv) > 6 else 50
        
        data_source = DataSource.LOWCAPS if data_source_str.lower() == "lowcaps" else DataSource.MAJORS
        timeframe_map = {
            "5m": Timeframe.M5,
            "15m": Timeframe.M15,
            "1h": Timeframe.H1,
            "4h": Timeframe.H4,
        }
        timeframe = timeframe_map.get(timeframe_str.lower(), Timeframe.M15)
        
        logger.info(f"Running catch-up: {data_source.value} {timeframe.value}, lookback={lookback_hours}h")
        result = rollup.catch_up_rollups(
            data_source=data_source,
            timeframe=timeframe,
            lookback_hours=lookback_hours,
            max_boundaries=max_boundaries,
            max_tokens=max_tokens
        )
        
        logger.info(f"Catch-up result: {result}")
        return
    
    # Default: Test 5m rollup for both majors and lowcaps
    logger.info("Testing 5m rollup...")
    
    # Test majors 5m rollup
    majors_written = rollup.rollup_timeframe(DataSource.MAJORS, Timeframe.M5)
    logger.info(f"Majors 5m rollup wrote {majors_written} bars")
    
    # Test lowcaps 5m rollup
    lowcaps_written = rollup.rollup_timeframe(DataSource.LOWCAPS, Timeframe.M5)
    logger.info(f"Lowcaps 5m rollup wrote {lowcaps_written} bars")
    
    logger.info(f"Total 5m rollup: {majors_written + lowcaps_written} bars")


if __name__ == "__main__":
    main()
