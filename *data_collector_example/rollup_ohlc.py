#!/usr/bin/env python3
"""
OHLC Rollup System

Converts 1-minute price points to 1m OHLC bars and rolls up to higher timeframes.

Process:
1. Convert 1m price points → 1m OHLC bars
2. Roll up 1m OHLC bars → higher timeframes (5m, 15m, 1h, 4h, 1d)

Usage:
    python rollup_ohlc.py                    # Rollup all configured timeframes
    python rollup_ohlc.py --timeframe 1m     # Rollup specific timeframe
    python rollup_ohlc.py --loop              # Run continuously
"""

import logging
import sys
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from collections import defaultdict
from supabase import create_client, Client

# Import configuration
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class OHLCBar:
    """OHLC bar data structure"""
    token_contract: str
    chain: str
    timeframe: str
    timestamp: datetime
    
    # Native prices
    open_native: float
    high_native: float
    low_native: float
    close_native: float
    
    # USD prices
    open_usd: float
    high_usd: float
    low_usd: float
    close_usd: float
    
    # Volume
    volume: float
    
    # Metadata
    source: str = "rollup"


class OHLCRollup:
    """OHLC rollup system"""
    
    def __init__(self):
        """Initialize the rollup system"""
        # Validate config
        errors = config.validate_config()
        if errors:
            logger.error("Configuration errors found:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration. Fix errors above.")
        
        # Initialize Supabase client
        self.sb: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Initialized OHLC rollup system")
    
    def rollup_timeframe(self, timeframe: str, when: Optional[datetime] = None) -> int:
        """
        Roll up data for a specific timeframe
        
        Args:
            timeframe: Target timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            when: Timestamp to rollup (default: now)
            
        Returns:
            Number of bars written
        """
        if when is None:
            when = datetime.now(tz=timezone.utc)
        
        # For 1m, just convert price points immediately
        if timeframe == "1m":
            bars = self._get_1m_price_points(timeframe, when)
            ohlc_bars = self._convert_1m_to_ohlc(bars)
            if not ohlc_bars:
                return 0
            written = self._store_ohlc_bars(ohlc_bars)
            logger.info(f"Converted {written} price points to 1m OHLC bars")
            return written
        
        # For higher timeframes, check if we're at a boundary and have enough data
        if not self._is_at_timeframe_boundary(when, timeframe):
            logger.debug(f"Not at {timeframe} boundary, skipping rollup")
            return 0
        
        # Check if bar already exists
        boundary_ts = self._get_timeframe_boundary_ts(when, timeframe)
        if self._bar_exists(timeframe, boundary_ts):
            logger.debug(f"{timeframe} bar already exists for {boundary_ts}, skipping")
            return 0
        
        # Get 1m OHLC data for the timeframe window
        bars = self._get_1m_ohlc_data(timeframe, when)
        
        # Check if we have enough bars
        required_bars = self._get_required_bars_count(timeframe)
        if len(bars) < required_bars:
            logger.info(f"Not enough 1m bars for {timeframe} rollup: have {len(bars)}, need {required_bars}")
            return 0
        
        # Roll up 1m OHLC bars to higher timeframe
        ohlc_bars = self._convert_to_ohlc(bars, timeframe)
        
        if not ohlc_bars:
            logger.info(f"No OHLC bars created for {timeframe} rollup")
            return 0
        
        # Store in database
        written = self._store_ohlc_bars(ohlc_bars)
        
        logger.info(f"Rolled up {written} {timeframe} bars at {boundary_ts}")
        return written
    
    def _get_1m_price_points(self, timeframe: str, when: datetime) -> List[Dict]:
        """Get 1m price points for 1m OHLC conversion"""
        # Get all price points that don't have corresponding OHLC bars yet
        # We'll get price points from the last 24 hours to catch up on any missed conversions
        start_time = when - timedelta(hours=24)
        
        # Get all price points
        price_points = self.sb.table(config.TABLE_1M_PRICE_DATA).select(
            "token_contract,chain,timestamp,price_usd,price_native,volume,volume_1m,volume_1h,volume_6h,volume_24h"
        ).gte("timestamp", start_time.isoformat()).lt(
            "timestamp", when.isoformat()
        ).order("timestamp", desc=False).execute()
        
        price_points_data = price_points.data or []
        
        if not price_points_data:
            return []
        
        # Get existing OHLC bars to find which price points are already converted
        existing_ohlc = self.sb.table(config.TABLE_OHLC_DATA).select(
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
        
        return unprocessed
    
    def _get_1m_ohlc_data(self, timeframe: str, when: datetime) -> List[Dict]:
        """Get 1m OHLC data for rollup to higher timeframe"""
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        
        # Get the boundary timestamp for this timeframe
        boundary_ts = self._get_timeframe_boundary_ts(when, timeframe)
        
        # Get 1m bars from the boundary period (e.g., last 15 minutes for 15m rollup)
        start_time = boundary_ts
        end_time = when
        
        # Get 1m OHLC data for the period
        result = self.sb.table(config.TABLE_OHLC_DATA).select(
            "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,"
            "open_native,high_native,low_native,close_native,volume"
        ).eq("timeframe", "1m").gte(
            "timestamp", start_time.isoformat()
        ).lt("timestamp", end_time.isoformat()).order(
            "timestamp", desc=False
        ).execute()
        
        ohlc_bars = result.data or []
        
        # For timeframes that need volume from price points (5m, 1h, 4h, 1d),
        # we need to also get the price points to access volume_1h, volume_6h, etc.
        if timeframe in ["5m", "1h", "4h", "1d"]:
            # Get price points for the same period to access volume data
            price_points_result = self.sb.table(config.TABLE_1M_PRICE_DATA).select(
                "token_contract,chain,timestamp,volume,volume_1h,volume_6h,volume_24h"
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
            for bar in ohlc_bars:
                bar_key = (bar['token_contract'], bar['chain'], bar['timestamp'])
                if bar_key in volume_lookup:
                    point = volume_lookup[bar_key]
                    bar['volume_5m'] = point.get('volume', 0)  # m5 volume
                    bar['volume_1h'] = point.get('volume_1h', 0)
                    bar['volume_6h'] = point.get('volume_6h', 0)
                    bar['volume_24h'] = point.get('volume_24h', 0)
        
        return ohlc_bars
    
    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """Get number of minutes for a timeframe"""
        timeframe_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        return timeframe_map.get(timeframe, 1)
    
    def _get_required_bars_count(self, timeframe: str) -> int:
        """Get the number of 1m bars required for a timeframe"""
        return self._get_timeframe_minutes(timeframe)
    
    def _is_at_timeframe_boundary(self, when: datetime, timeframe: str) -> bool:
        """Check if we're at a timeframe boundary"""
        if timeframe == "15m":
            # 15m boundaries: :00, :15, :30, :45
            return when.minute % 15 == 0 and when.second < 60
        elif timeframe == "1h":
            # 1h boundaries: :00
            return when.minute == 0 and when.second < 60
        elif timeframe == "4h":
            # 4h boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
            return when.hour % 4 == 0 and when.minute == 0 and when.second < 60
        elif timeframe == "1d":
            # 1d boundaries: 00:00
            return when.hour == 0 and when.minute == 0 and when.second < 60
        elif timeframe == "5m":
            # 5m boundaries: :00, :05, :10, :15, etc.
            return when.minute % 5 == 0 and when.second < 60
        else:
            return False
    
    def _get_timeframe_boundary_ts(self, when: datetime, timeframe: str) -> datetime:
        """Get the timeframe boundary timestamp for a given time"""
        return self._get_timeframe_boundary(when, self._get_timeframe_minutes(timeframe))
    
    def _bar_exists(self, timeframe: str, boundary_ts: datetime) -> bool:
        """Check if a rollup bar already exists for this timeframe and boundary"""
        try:
            # Get all tokens we're tracking
            tokens = config.TOKENS_TO_TRACK
            
            # Check if any bar exists for any token at this boundary
            result = self.sb.table(config.TABLE_OHLC_DATA).select(
                "token_contract"
            ).eq("timeframe", timeframe).eq(
                "timestamp", boundary_ts.isoformat()
            ).limit(1).execute()
            
            return len(result.data or []) > 0
        except Exception as e:
            logger.error(f"Error checking if bar exists: {e}")
            return False
    
    def _convert_1m_to_ohlc(self, bars: List[Dict]) -> List[OHLCBar]:
        """
        Convert 1m price points to 1m OHLC bars
        
        Logic:
        - Open = Previous candle's close (or first price if no previous)
        - Close = Current price
        - High = max(open, close)
        - Low = min(open, close)
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
                volumes = [float(b.get('volume', 0) or 0) for b in minute_bars]
                
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
                    volumes_5m = [float(b.get('volume', 0) or 0) for b in minute_bars]
                    volume = sum(volumes_5m) / 5.0 if volumes_5m else 0
                
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
                    source="1m_conversion"
                )
                ohlc_bars.append(ohlc_bar)
                
                # Update previous close for next iteration
                previous_close_usd = close_price_usd
                previous_close_native = close_price_native
        
        return ohlc_bars
    
    def _convert_to_ohlc(self, bars: List[Dict], timeframe: str) -> List[OHLCBar]:
        """
        Convert 1m OHLC bars to higher timeframe OHLC bars
        
        Args:
            bars: List of 1m OHLC bars
            timeframe: Target timeframe (5m, 15m, 1h, 4h, 1d)
            
        Returns:
            List of OHLCBar objects
        """
        if not bars:
            return []
        
        # Group bars by token_contract and chain
        grouped_bars = defaultdict(list)
        for bar in bars:
            key = (bar['token_contract'], bar['chain'])
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
                
                # Calculate timeframe boundary
                timeframe_key = self._get_timeframe_boundary(ts, timeframe_minutes)
                timeframe_bars[timeframe_key].append(bar)
            
            # For rollup, we should only have one period (the boundary period)
            # But we'll handle multiple periods just in case
            for timeframe_ts, period_bars in timeframe_bars.items():
                if not period_bars:
                    continue
                
                # Sort by timestamp to get proper OHLC
                period_bars.sort(key=lambda x: x['timestamp'])
                
                # Calculate OHLC from 1m bars
                open_price_usd = float(period_bars[0]['open_usd'])
                close_price_usd = float(period_bars[-1]['close_usd'])
                high_price_usd = max(float(bar['high_usd']) for bar in period_bars)
                low_price_usd = min(float(bar['low_usd']) for bar in period_bars)
                
                open_price_native = float(period_bars[0]['open_native'])
                close_price_native = float(period_bars[-1]['close_native'])
                high_price_native = max(float(bar['high_native']) for bar in period_bars)
                low_price_native = min(float(bar['low_native']) for bar in period_bars)
                
                # Volume depends on timeframe:
                # - 5m: use m5 directly from latest price point in period
                # - 15m: sum of 1m volumes
                # - 1h: use h1 directly from latest price point in period
                # - 4h: use h6 * 4/6 from latest price point in period
                # - 1d: use h24 directly from latest price point in period
                
                if timeframe == "5m":
                    # Use m5 volume from latest 1m bar in the period (from price point)
                    latest_bar = period_bars[-1]
                    volume = float(latest_bar.get('volume_5m', latest_bar.get('volume', 0)) or 0)  # m5 volume
                elif timeframe == "15m":
                    # Sum of 1m volumes from OHLC bars
                    volume = sum(float(bar.get('volume', 0) or 0) for bar in period_bars)
                elif timeframe == "1h":
                    # Use h1 volume from latest 1m bar in the period (from price point)
                    latest_bar = period_bars[-1]
                    volume = float(latest_bar.get('volume_1h', 0) or 0)
                elif timeframe == "4h":
                    # Use h6 * 4/6 from latest 1m bar in the period (from price point)
                    latest_bar = period_bars[-1]
                    volume_6h = float(latest_bar.get('volume_6h', 0) or 0)
                    volume = volume_6h * (4.0 / 6.0)  # 4h / 6h = 2/3
                elif timeframe == "1d":
                    # Use h24 volume from latest 1m bar in the period (from price point)
                    latest_bar = period_bars[-1]
                    volume = float(latest_bar.get('volume_24h', 0) or 0)
                else:
                    # Fallback: sum of 1m volumes
                    volume = sum(float(bar.get('volume', 0) or 0) for bar in period_bars)
                
                # Create OHLC bar with the boundary timestamp
                ohlc_bar = OHLCBar(
                    token_contract=token_contract,
                    chain=chain,
                    timeframe=timeframe,
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
                    source="rollup"
                )
                ohlc_bars.append(ohlc_bar)
        
        return ohlc_bars
    
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
    
    def _store_ohlc_bars(self, bars: List[OHLCBar]) -> int:
        """Store OHLC bars in database"""
        if not bars:
            return 0
        
        # Convert OHLCBar objects to database rows
        rows = []
        for bar in bars:
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
                "source": bar.source
            }
            rows.append(row)
        
        try:
            # Upsert to handle duplicates
            result = self.sb.table(config.TABLE_OHLC_DATA).upsert(
                rows,
                on_conflict="token_contract,chain,timeframe,timestamp"
            ).execute()
            
            logger.info(f"Stored {len(rows)} bars in {config.TABLE_OHLC_DATA}")
            return len(rows)
            
        except Exception as e:
            logger.error(f"Error storing OHLC bars: {e}")
            return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Rollup OHLC data to higher timeframes")
    parser.add_argument(
        '--timeframe',
        type=str,
        help='Specific timeframe to rollup (1m, 5m, 15m, 1h, 4h, 1d). If not specified, rollup all configured timeframes.'
    )
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Run continuously'
    )
    
    args = parser.parse_args()
    
    try:
        rollup = OHLCRollup()
        
        if args.loop:
            # Run in loop (would need asyncio for proper scheduling)
            logger.info("Loop mode not yet implemented. Run manually or use cron.")
            return
        
        # Determine which timeframes to rollup
        if args.timeframe:
            if args.timeframe not in config.ROLLUP_TIMEFRAMES:
                logger.error(f"Timeframe {args.timeframe} not in configured timeframes: {config.ROLLUP_TIMEFRAMES}")
                sys.exit(1)
            timeframes = [args.timeframe]
        else:
            timeframes = config.ROLLUP_TIMEFRAMES
        
        # Rollup each timeframe
        total_written = 0
        for timeframe in timeframes:
            written = rollup.rollup_timeframe(timeframe)
            total_written += written
            logger.info(f"Rolled up {written} bars for {timeframe}")
        
        logger.info(f"Total bars written: {total_written}")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

