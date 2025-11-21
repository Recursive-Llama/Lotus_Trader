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
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union
from enum import Enum

from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)


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


class GenericOHLCRollup:
    """Generic OHLC rollup system for both majors and lowcaps"""
    
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
        self.logger = logging.getLogger(__name__)
    
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
        
        # For 1m, just convert price points immediately (no boundary check needed)
        if timeframe == Timeframe.M1:
            if data_source == DataSource.MAJORS:
                # Majors already have OHLC data, skip 1m conversion
                self.logger.info("Majors data already in OHLC format, skipping 1m conversion")
                return 0
            else:
                # Get unprocessed price points for 1m OHLC conversion
                bars = self._get_lowcap_1m_data(timeframe, when)
                if not bars:
                    self.logger.info(f"No unprocessed price points found for 1m OHLC conversion")
                    return 0
                ohlc_bars = self._convert_1m_to_ohlc(bars)
                if not ohlc_bars:
                    return 0
                written = self._store_ohlc_bars(data_source, ohlc_bars)
                self.logger.info(f"Converted {written} price points to 1m OHLC bars")
                return written
        
        # For higher timeframes, check if we're at a boundary and have enough data
        if not self._is_at_timeframe_boundary(when, timeframe):
            self.logger.debug(f"Not at {timeframe.value} boundary, skipping rollup")
            return 0
        
        # Check if bar already exists
        boundary_ts = self._get_timeframe_boundary_ts(when, timeframe)
        if self._bar_exists(data_source, timeframe, boundary_ts):
            self.logger.debug(f"{timeframe.value} bar already exists for {boundary_ts}, skipping")
            return 0
        
        self.logger.info(f"Rolling up {data_source.value} data to {timeframe.value} at {when}")
        
        # Get 1m data for the timeframe window
        if data_source == DataSource.MAJORS:
            bars = self._get_majors_1m_data(timeframe, when)
        else:
            bars = self._get_lowcap_1m_data(timeframe, when)
        
        if not bars:
            self.logger.info(f"No 1m data found for {data_source.value} {timeframe.value}")
            return 0
        
        # Check if we have enough bars
        required_bars = self._get_required_bars_count(timeframe)
        if len(bars) < required_bars:
            self.logger.info(f"Not enough 1m bars for {timeframe.value} rollup: have {len(bars)}, need {required_bars}")
            return 0
        
        # Convert to OHLC bars
        ohlc_bars = self._convert_to_ohlc(bars, timeframe)
        
        if not ohlc_bars:
            self.logger.info(f"No OHLC bars created for {timeframe.value} rollup")
            return 0
        
        # Store in database
        written = self._store_ohlc_bars(data_source, ohlc_bars)
        
        self.logger.info(f"Rolled up {written} {timeframe.value} bars at {boundary_ts}")
        return written
    
    def _get_majors_1m_data(self, timeframe: Timeframe, when: datetime) -> List[Dict]:
        """Get majors 1m data from majors_price_data_ohlc (timeframe='1m') for the timeframe window"""
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        start_time = when - timedelta(minutes=timeframe_minutes)
        
        # Read from majors_price_data_ohlc with timeframe='1m'
        result = self.sb.table("majors_price_data_ohlc").select(
            "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume"
        ).eq("chain", "hyperliquid").eq("timeframe", "1m").gte("timestamp", start_time.isoformat()).lt("timestamp", when.isoformat()).order("timestamp", desc=False).execute()
        
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
    
    def _get_lowcap_1m_data(self, timeframe: Timeframe, when: datetime) -> List[Dict]:
        """Get lowcap data for the timeframe window"""
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        
        # For 1m timeframe, we need raw price points (not OHLC data)
        if timeframe == Timeframe.M1:
            self.logger.info("Getting 1m price points for 1m OHLC conversion")
            # Get all price points from the last 24 hours to catch up on any missed conversions
            start_time = when - timedelta(hours=24)
            
            # Get all price points
            result = self.sb.table("lowcap_price_data_1m").select(
                "token_contract,chain,timestamp,price_usd,price_native,volume_5m,volume_1m,volume_1h,volume_6h,volume_24h,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
            ).gte("timestamp", start_time.isoformat()).lt("timestamp", when.isoformat()).order("timestamp", desc=False).execute()
            
            price_points_data = result.data or []
            
            if not price_points_data:
                return []
            
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
            
            self.logger.info(f"Found {len(unprocessed)} unprocessed price points out of {len(price_points_data)} total")
            return unprocessed
        
        # For higher timeframes, prioritize existing OHLC data (15m) for rollup
        # because 15m data has proper OHLC format and covers more history
        
        # First try 1m OHLC data from OHLC table (preferred for rollup)
        self.logger.info(f"Trying 1m OHLC data first for {timeframe.value} rollup")
        start_time = when - timedelta(minutes=timeframe_minutes * 2)
        
        # Use pagination to get all records (Supabase has 1000 record limit)
        all_data = []
        page_size = 1000
        offset = 0
        
        while True:
            result = self.sb.table("lowcap_price_data_ohlc").select(
                "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
            ).eq("timeframe", "1m").gte("timestamp", start_time.isoformat()).lt("timestamp", when.isoformat()).order("timestamp", desc=False).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
                
            all_data.extend(result.data)
            
            # If we got less than page_size, we've reached the end
            if len(result.data) < page_size:
                break
                
            offset += page_size
        
        if all_data:
            # For timeframes that need volume from price points (5m, 1h, 4h, 1d),
            # we need to also get the price points to access volume_1h, volume_6h, etc.
            if timeframe in [Timeframe.M5, Timeframe.H1, Timeframe.H4, Timeframe.D1]:
                # Get price points for the same period to access volume data
                price_points_result = self.sb.table("lowcap_price_data_1m").select(
                    "token_contract,chain,timestamp,volume_5m,volume_1h,volume_6h,volume_24h,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
                ).gte(
                    "timestamp", start_time.isoformat()
                ).lt("timestamp", when.isoformat()).order(
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
        self.logger.info("No 1m OHLC data found, trying 15m OHLC data")
        all_data = []
        offset = 0
        
        while True:
            result = self.sb.table("lowcap_price_data_ohlc").select(
                "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
            ).eq("timeframe", "15m").gte("timestamp", start_time.isoformat()).lt("timestamp", when.isoformat()).order("timestamp", desc=False).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
                
            all_data.extend(result.data)
            
            if len(result.data) < page_size:
                break
                
            offset += page_size
        
        if all_data:
            return all_data
        
        # Final fallback to raw 1m price points
        self.logger.info("No OHLC data found, falling back to raw 1m price points")
        result = self.sb.table("lowcap_price_data_1m").select(
            "token_contract,chain,timestamp,price_usd,price_native,volume_1m,liquidity_usd,liquidity_change_1m,price_change_24h,market_cap,fdv,dex_id,pair_address"
        ).gte("timestamp", start_time.isoformat()).lt("timestamp", when.isoformat()).order("timestamp", desc=False).execute()
        
        return result.data or []
    
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
        """Check if a rollup bar already exists for this timeframe and boundary"""
        try:
            table_name = "majors_price_data_ohlc" if data_source == DataSource.MAJORS else "lowcap_price_data_ohlc"
            
            # Check if any bar exists for any token at this boundary
            result = self.sb.table(table_name).select(
                "token_contract"
            ).eq("timeframe", timeframe.value).eq(
                "timestamp", boundary_ts.isoformat()
            ).limit(1).execute()
            
            return len(result.data or []) > 0
        except Exception as e:
            self.logger.error(f"Error checking if bar exists: {e}")
            return False
    
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
                
                # Validate: we need at least timeframe_minutes worth of 1m bars for a meaningful bar
                # For example, a 4h bar (240 minutes) should have at least 240 1m bars
                # Allow some tolerance (e.g., 80% of expected bars) to account for missing data
                min_required_bars = int(timeframe_minutes * 0.8)
                if len(period_bars) < min_required_bars:
                    self.logger.debug(
                        f"Skipping {timeframe.value} bar at {timeframe_ts} for {token_contract}: "
                        f"only {len(period_bars)} 1m bars (need at least {min_required_bars} for {timeframe_minutes}min timeframe)"
                    )
                    continue
                    
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
                    source="rollup",
                    **metadata
                )
                ohlc_bars.append(ohlc_bar)
        
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
                    source="1m_conversion"
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
    
    def _store_ohlc_bars(self, data_source: DataSource, bars: List[OHLCBar]) -> int:
        """Store OHLC bars in the appropriate table"""
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
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    
    rollup = GenericOHLCRollup()
    
    # Test 5m rollup for both majors and lowcaps
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
