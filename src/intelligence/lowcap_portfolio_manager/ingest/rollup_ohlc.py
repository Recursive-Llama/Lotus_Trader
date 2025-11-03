"""
Generic OHLC Rollup System

Rolls up 1m data to higher timeframes (5m, 15m, 1h, 4h, 1d) for both majors and lowcaps.

Input Sources:
- majors_price_data_1m (already OHLC bars)
- lowcap_price_data_1m (price points, needs OHLC conversion)

Output Tables:
- majors_price_data_ohlc
- lowcap_price_data_ohlc

Timeframes: 5m, 15m, 1h, 4h, 1d
Prices: Both native and USD prices
Volume: Sum of 1m volumes for timeframe
"""

from __future__ import annotations

import logging
import os
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
            timeframe: Target timeframe (5m, 15m, 1h, 4h, 1d)
            when: Timestamp to rollup (default: now)
            
        Returns:
            Number of bars written
        """
        if when is None:
            when = datetime.now(tz=timezone.utc)
        
        self.logger.info(f"Rolling up {data_source.value} data to {timeframe.value} at {when}")
        
        # Get 1m data for the timeframe window
        if data_source == DataSource.MAJORS:
            bars = self._get_majors_1m_data(timeframe, when)
        else:
            bars = self._get_lowcap_1m_data(timeframe, when)
        
        if not bars:
            self.logger.info(f"No 1m data found for {data_source.value} {timeframe.value}")
            return 0
        
        # Convert to OHLC bars
        ohlc_bars = self._convert_to_ohlc(bars, timeframe)
        
        # Store in database
        written = self._store_ohlc_bars(data_source, ohlc_bars)
        
        self.logger.info(f"Rolled up {written} {timeframe.value} bars for {data_source.value}")
        return written
    
    def _get_majors_1m_data(self, timeframe: Timeframe, when: datetime) -> List[Dict]:
        """Get majors 1m data for the timeframe window"""
        timeframe_minutes = self._get_timeframe_minutes(timeframe)
        start_time = when - timedelta(minutes=timeframe_minutes)
        
        result = self.sb.table("majors_price_data_1m").select(
            "token,ts,open,high,low,close,volume"
        ).gte("ts", start_time.isoformat()).lt("ts", when.isoformat()).order("ts", desc=False).execute()
        
        # Convert majors format to match lowcap format
        converted_data = []
        for bar in (result.data or []):
            converted_data.append({
                'token_contract': bar['token'],  # Use token as contract for majors
                'chain': 'hyperliquid',  # Majors are from Hyperliquid
                'timestamp': bar['ts'],
                'open_usd': float(bar['open']),
                'high_usd': float(bar['high']),
                'low_usd': float(bar['low']),
                'close_usd': float(bar['close']),
                'open_native': float(bar['open']),  # Majors are already in USD
                'high_native': float(bar['high']),
                'low_native': float(bar['low']),
                'close_native': float(bar['close']),
                'volume_change_1m': float(bar['volume'])
            })
        
        return converted_data
    
    def _get_lowcap_1m_data(self, timeframe: Timeframe, when: datetime) -> List[Dict]:
        """Get lowcap data for the timeframe window (prioritizes 15m OHLC data)"""
        # For historical rollup, prioritize 15m OHLC data over 1m data
        # because 15m data has proper OHLC format and covers more history
        
        # First try 15m data from OHLC table (preferred)
        self.logger.info("Trying 15m OHLC data first")
        
        # Use pagination to get all records (Supabase has 1000 record limit)
        all_data = []
        page_size = 1000
        offset = 0
        
        while True:
            result = self.sb.table("lowcap_price_data_ohlc").select(
                "token_contract,chain,timestamp,open_usd,high_usd,low_usd,close_usd,open_native,high_native,low_native,close_native,volume"
            ).eq("timeframe", "15m").lt("timestamp", when.isoformat()).order("timestamp", desc=False).range(offset, offset + page_size - 1).execute()
            
            if not result.data:
                break
                
            all_data.extend(result.data)
            
            # If we got less than page_size, we've reached the end
            if len(result.data) < page_size:
                break
                
            offset += page_size
        
        if all_data:
            # Just rename volume to volume_change_1m to match expected format
            for bar in all_data:
                bar["volume_change_1m"] = bar.pop("volume")
            return all_data
        
        # Fallback to 1m data if no 15m data available
        self.logger.info("No 15m data found, trying 1m data")
        result = self.sb.table("lowcap_price_data_1m").select(
            "token_contract,chain,timestamp,price_usd,price_native,volume_change_1m"
        ).lt("timestamp", when.isoformat()).order("timestamp", desc=False).execute()
        
        return result.data or []
    
    def _get_timeframe_minutes(self, timeframe: Timeframe) -> int:
        """Get number of minutes for a timeframe"""
        timeframe_map = {
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440
        }
        return timeframe_map[timeframe]
    
    def _convert_to_ohlc(self, bars: List[Dict], timeframe: Timeframe) -> List[OHLCBar]:
        """Convert 1m data to OHLC bars for the timeframe"""
        if not bars:
            return []
        
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
            from collections import defaultdict
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
                    
                # Sort by timestamp to get proper OHLC
                period_bars.sort(key=lambda x: x['timestamp'])
                
                # Check if we have OHLC data (from 15m backfill) or price points (from 1m data)
                has_ohlc_data = 'open_usd' in period_bars[0]
                
                if has_ohlc_data:
                    # Calculate OHLC from actual OHLC data (15m bars)
                    open_price_usd = float(period_bars[0]['open_usd'])
                    close_price_usd = float(period_bars[-1]['close_usd'])
                    high_price_usd = max(float(bar['high_usd']) for bar in period_bars)
                    low_price_usd = min(float(bar['low_usd']) for bar in period_bars)
                    
                    open_price_native = float(period_bars[0]['open_native'])
                    close_price_native = float(period_bars[-1]['close_native'])
                    high_price_native = max(float(bar['high_native']) for bar in period_bars)
                    low_price_native = min(float(bar['low_native']) for bar in period_bars)
                    
                    volume = sum(float(bar.get('volume_change_1m', bar.get('volume', 0)) or 0) for bar in period_bars)
                else:
                    # Calculate OHLC from price points (1m data)
                    prices_usd = [float(bar['price_usd']) for bar in period_bars]
                    prices_native = [float(bar['price_native']) for bar in period_bars]
                    
                    open_price_usd = prices_usd[0]
                    close_price_usd = prices_usd[-1]
                    high_price_usd = max(prices_usd)
                    low_price_usd = min(prices_usd)
                    
                    open_price_native = prices_native[0]
                    close_price_native = prices_native[-1]
                    high_price_native = max(prices_native)
                    low_price_native = min(prices_native)
                    
                    volume = sum(float(bar.get('volume_change_1m', 0) or 0) for bar in period_bars)
                
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
                    source="rollup"
                )
                ohlc_bars.append(ohlc_bar)
        
        return ohlc_bars
    
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
