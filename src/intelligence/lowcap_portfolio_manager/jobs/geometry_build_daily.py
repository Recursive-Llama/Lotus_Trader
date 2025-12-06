"""
Daily geometry builder: computes per-token horizontal S/R and diagonals, stores in positions.features.geometry.

Algorithm (v1):
- Pull last N bars (default 7d of 1m or 5m downsampled) per active position
- Find swing highs/lows with prominence heuristic
- Cluster swing prices into S/R levels; score strength/confidence
- Fit robust diagonals (Theil–Sen) through highs (downtrend) and lows (uptrend)
- Store levels and diagonals with metadata; no runtime flags here (tracker will update hourly)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple, Optional
import json
import requests  # type: ignore
# Set non-GUI backend before importing pyplot (prevents macOS crash on background threads)
import matplotlib
matplotlib.use('Agg')  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore

from supabase import create_client, Client  # type: ignore
from statistics import median

from src.intelligence.lowcap_portfolio_manager.spiral.persist import SpiralPersist


logger = logging.getLogger(__name__)


class GeometryBuilder:
    def __init__(self, timeframe: str = "1h", generate_charts: bool = True) -> None:
        """
        Initialize Geometry Builder.
        
        Args:
            timeframe: Timeframe to process ("1m", "15m", "1h", "4h")
            generate_charts: Whether to generate chart images
        """
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(supabase_url, supabase_key)
        self.persist = SpiralPersist()
        self.lookback_days = int(os.getenv("GEOM_LOOKBACK_DAYS", "14"))
        self.generate_charts = generate_charts
        self.timeframe = timeframe

    def _active_positions(self) -> List[Dict[str, Any]]:
        """Get positions for this timeframe (watchlist + active only)."""
        res = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,timeframe")
            .eq("timeframe", self.timeframe)
            .in_("status", ["watchlist", "active"])  # Process watchlist and active
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _fetch_bars(self, contract: str, chain: str, end: datetime, minutes: int = None) -> List[Dict[str, Any]]:
        """Fetch OHLC bars for the specified timeframe."""
        # If minutes is None, fetch all available data
        if minutes is not None:
            start = end - timedelta(minutes=minutes)
            # Use OHLC data for the specified timeframe
            res = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp, high_usd, low_usd, close_usd, volume")
                .eq("token_contract", contract)
                .eq("chain", chain)
                .eq("timeframe", self.timeframe)  # Use timeframe-specific data
                .gte("timestamp", start.isoformat())
                .lte("timestamp", end.isoformat())
                .gt("close_usd", 0)  # Filter out zero-price bars (no trading)
                .order("timestamp", desc=False)
                .execute()
            )
        else:
            # Fetch all available data
            res = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp, high_usd, low_usd, close_usd, volume")
                .eq("token_contract", contract)
                .eq("chain", chain)
                .eq("timeframe", self.timeframe)  # Use timeframe-specific data
                .lte("timestamp", end.isoformat())
                .gt("close_usd", 0)  # Filter out zero-price bars (no trading)
                .order("timestamp", desc=False)
                .execute()
            )
        return res.data or []

    def _get_swing_points_with_coordinates(self, timestamps: List[datetime], highs: List[float], lows: List[float], closes: List[float]) -> List[Dict[str, Any]]:
        """Get swing points with their coordinates (timestamps and prices)"""
        if len(timestamps) < 3:
            return []
        
        # Find all swing highs and lows first
        swing_highs, swing_lows = self._swings_percentage_based(closes, prominence_threshold=0.5)
        
        # Extract swing points with their values
        swing_points = []
        for i in swing_highs:
            swing_points.append({
                'index': i,
                'timestamp': timestamps[i].isoformat(),  # Convert datetime to ISO string
                'price': highs[i],
                'type': 'high'
            })
        for i in swing_lows:
            swing_points.append({
                'index': i,
                'timestamp': timestamps[i].isoformat(),  # Convert datetime to ISO string
                'price': lows[i],
                'type': 'low'
            })
        
        # Sort by timestamp
        swing_points.sort(key=lambda x: x['timestamp'])
        return swing_points

    def _swings_percentage_based(self, closes: List[float], prominence_threshold: float = 0.5) -> Tuple[List[int], List[int]]:
        """Find swing highs and lows using percentage-based prominence (more adaptive than ATR)"""
        highs: List[int] = []
        lows: List[int] = []
        
        for i in range(2, len(closes) - 2):
            c = closes[i]
            
            # Check for swing high (5-bar pattern)
            if c > closes[i - 1] and c > closes[i - 2] and c > closes[i + 1] and c > closes[i + 2]:
                # Calculate percentage prominence
                window = closes[i - 2:i + 3]
                min_in_window = min(window)
                if c > 0:  # Avoid division by zero
                    percentage_prominence = (c - min_in_window) / c * 100
                    if percentage_prominence >= prominence_threshold:
                        highs.append(i)
            
            # Check for swing low (5-bar pattern)
            if c < closes[i - 1] and c < closes[i - 2] and c < closes[i + 1] and c < closes[i + 2]:
                # Calculate percentage prominence
                window = closes[i - 2:i + 3]
                max_in_window = max(window)
                if c > 0:  # Avoid division by zero
                    percentage_prominence = (max_in_window - c) / c * 100
                    if percentage_prominence >= prominence_threshold:
                        lows.append(i)
        
        return highs, lows

    def _find_ath_atl_pivots(self, timestamps: List[datetime], closes: List[float], highs: List[float], lows: List[float]) -> List[Dict[str, Any]]:
        """Find ATH and ATL pivots to define sustained trend segments using OHLC extremes"""
        if len(timestamps) < 3:
            return []
        
        # Find all swing highs and lows first
        swing_highs, swing_lows = self._swings_percentage_based(closes, prominence_threshold=0.5)
        
        # Extract swing points with their values
        swing_points = []
        for i in swing_highs:
            swing_points.append({
                'index': i,
                'timestamp': timestamps[i],
                'price': highs[i],
                'type': 'high'
            })
        for i in swing_lows:
            swing_points.append({
                'index': i,
                'timestamp': timestamps[i],
                'price': lows[i],
                'type': 'low'
            })
        
        # Sort by timestamp
        swing_points.sort(key=lambda x: x['timestamp'])
        
        # Find ATH and ATL
        ath = max(swing_points, key=lambda x: x['price'])
        atl = min(swing_points, key=lambda x: x['price'])
        
        # Determine what comes first
        if ath['timestamp'] < atl['timestamp']:
            # ATH comes first
            # Find ATL before ATH
            atl_before = None
            for point in swing_points:
                if point['type'] == 'low' and point['timestamp'] < ath['timestamp']:
                    if atl_before is None or point['price'] < atl_before['price']:
                        atl_before = point
            
            # Find ATL after ATH
            atl_after = None
            for point in swing_points:
                if point['type'] == 'low' and point['timestamp'] > ath['timestamp']:
                    if atl_after is None or point['price'] < atl_after['price']:
                        atl_after = point
            
            # Create trend segments
            segments = []
            if atl_before:
                segments.append({
                    'start': atl_before,
                    'end': ath,
                    'type': 'uptrend',
                    'name': 'ATL to ATH'
                })
            if atl_after:
                segments.append({
                    'start': ath,
                    'end': atl_after,
                    'type': 'downtrend',
                    'name': 'ATH to ATL'
                })
            
        else:
            # ATL comes first
            # Find ATH after ATL
            ath_after = None
            for point in swing_points:
                if point['type'] == 'high' and point['timestamp'] > atl['timestamp']:
                    if ath_after is None or point['price'] > ath_after['price']:
                        ath_after = point
            
            # Find ATL after ATH
            atl_after_ath = None
            if ath_after:
                for point in swing_points:
                    if point['type'] == 'low' and point['timestamp'] > ath_after['timestamp']:
                        if atl_after_ath is None or point['price'] < atl_after_ath['price']:
                            atl_after_ath = point
            
            # Create trend segments
            segments = []
            if ath_after:
                segments.append({
                    'start': atl,
                    'end': ath_after,
                    'type': 'uptrend',
                    'name': 'ATL to ATH'
                })
            if atl_after_ath:
                segments.append({
                    'start': ath_after,
                    'end': atl_after_ath,
                    'type': 'downtrend',
                    'name': 'ATH to ATL'
                })
        
        return segments

    def _detect_trends_proper(self, timestamps: List[datetime], closes: List[float], highs: List[float], lows: List[float]) -> List[Dict[str, Any]]:
        """Proper trend detection: Find first trend using ATL/ATH, then detect subsequent trend changes"""
        if len(timestamps) < 3:
            return []
        
        # Find all swing highs and lows first
        swing_highs, swing_lows = self._swings_percentage_based(closes, prominence_threshold=0.5)
        
        # Extract swing points with their values
        swing_points = []
        for i in swing_highs:
            swing_points.append({
                'index': i,
                'timestamp': timestamps[i],
                'price': highs[i],
                'type': 'high'
            })
        for i in swing_lows:
            swing_points.append({
                'index': i,
                'timestamp': timestamps[i],
                'price': lows[i],
                'type': 'low'
            })
        
        # Sort by timestamp
        swing_points.sort(key=lambda x: x['timestamp'])
        
        # Find ATH and ATL
        ath = max(swing_points, key=lambda x: x['price'])
        atl = min(swing_points, key=lambda x: x['price'])
        
        # Determine first trend based on which comes first
        if ath['timestamp'] < atl['timestamp']:
            # ATH comes first - first trend is downtrend
            first_trend_type = 'downtrend'
            first_trend_start = ath
            first_trend_end = atl
        else:
            # ATL comes first - first trend is uptrend
            first_trend_type = 'uptrend'
            first_trend_start = atl
            first_trend_end = ath
        
        # Initialize trend segments
        trend_segments = [{
            'start': first_trend_start,
            'end': first_trend_end,
            'type': first_trend_type,
            'name': f'First {first_trend_type}'
        }]
        
        # Now detect subsequent trend changes dynamically
        current_trend_type = first_trend_type
        current_trend_end = first_trend_end
        
        # Continue detecting trends until end of data
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Generate trendlines for current trend
            current_trendlines = self._generate_trendlines_for_segment(
                timestamps, closes, swing_highs, swing_lows, current_trend_type
            )
            
            if not current_trendlines:
                break
            
            # Find the primary trendline for break detection
            if current_trend_type == 'uptrend':
                # Look for uptrend support line (lows)
                primary_trendline = None
                for tl in current_trendlines:
                    if tl.get('type') == 'uptrend_lows':
                        if primary_trendline is None or tl.get('r2_score', 0) > primary_trendline.get('r2_score', 0):
                            primary_trendline = tl
                
                if not primary_trendline:
                    break
                
                # Look for 3 swing highs below the uptrend support
                swing_highs_after_end = [i for i in swing_highs if timestamps[i] > current_trend_end['timestamp']]
                breaks_below = []
                
                for swing_idx in swing_highs_after_end:
                    swing_time = timestamps[swing_idx]
                    swing_price = closes[swing_idx]
                    
                    # Calculate trendline price at this time
                    hours_diff = (swing_time - datetime.fromisoformat(primary_trendline['anchor_time_iso'].replace('Z', '+00:00'))).total_seconds() / 3600
                    trendline_price = primary_trendline['intercept'] + primary_trendline['slope'] * hours_diff
                    
                    if swing_price < trendline_price:
                        breaks_below.append(swing_idx)
                
                if len(breaks_below) >= 3:
                    # Trend change: uptrend -> downtrend
                    # Find the swing point corresponding to the first break
                    first_break_idx = min(breaks_below)
                    trend_change_point = None
                    for sp in swing_points:
                        if sp['index'] == first_break_idx:
                            trend_change_point = sp
                            break
                    
                    if trend_change_point:
                        new_trend_type = 'downtrend'
                        
                        # Find end of new downtrend (next significant low)
                        swing_lows_after_change = [sp for sp in swing_points if sp['timestamp'] > trend_change_point['timestamp'] and sp['type'] == 'low']
                        if swing_lows_after_change:
                            new_trend_end = min(swing_lows_after_change, key=lambda x: x['price'])
                            
                            trend_segments.append({
                                'start': trend_change_point,
                                'end': new_trend_end,
                                'type': new_trend_type,
                                'name': f'{current_trend_type} to {new_trend_type}'
                            })
                            
                            current_trend_type = new_trend_type
                            current_trend_end = new_trend_end
                            continue
            
            else:  # current_trend_type == 'downtrend'
                # Look for downtrend resistance line (highs)
                primary_trendline = None
                for tl in current_trendlines:
                    if tl.get('type') == 'downtrend_highs':
                        if primary_trendline is None or tl.get('r2_score', 0) > primary_trendline.get('r2_score', 0):
                            primary_trendline = tl
                
                if not primary_trendline:
                    break
                
                # Look for 3 swing lows above the downtrend resistance
                swing_lows_after_end = [i for i in swing_lows if timestamps[i] > current_trend_end['timestamp']]
                breaks_above = []
                
                for swing_idx in swing_lows_after_end:
                    swing_time = timestamps[swing_idx]
                    swing_price = closes[swing_idx]
                    
                    # Calculate trendline price at this time
                    hours_diff = (swing_time - datetime.fromisoformat(primary_trendline['anchor_time_iso'].replace('Z', '+00:00'))).total_seconds() / 3600
                    trendline_price = primary_trendline['intercept'] + primary_trendline['slope'] * hours_diff
                    
                    if swing_price > trendline_price:
                        breaks_above.append(swing_idx)
                
                if len(breaks_above) >= 3:
                    # Trend change: downtrend -> uptrend
                    # Find the swing point corresponding to the first break
                    first_break_idx = min(breaks_above)
                    trend_change_point = None
                    for sp in swing_points:
                        if sp['index'] == first_break_idx:
                            trend_change_point = sp
                            break
                    
                    if trend_change_point:
                        new_trend_type = 'uptrend'
                        
                        # Find end of new uptrend (next significant high)
                        swing_highs_after_change = [sp for sp in swing_points if sp['timestamp'] > trend_change_point['timestamp'] and sp['type'] == 'high']
                        if swing_highs_after_change:
                            new_trend_end = max(swing_highs_after_change, key=lambda x: x['price'])
                            
                            trend_segments.append({
                                'start': trend_change_point,
                                'end': new_trend_end,
                                'type': new_trend_type,
                                'name': f'{current_trend_type} to {new_trend_type}'
                            })
                            
                            current_trend_type = new_trend_type
                            current_trend_end = new_trend_end
                            continue
            
            # No trend change detected, break the loop
            break
        
        return trend_segments

    def _detect_trend_changes(self, timestamps: List[datetime], closes: List[float], 
                             swing_highs: List[int], swing_lows: List[int], 
                             existing_trendlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect trend changes using 3-swing confirmation logic"""
        trend_changes = []
        # Guard rails to reduce false flips
        min_pre_bars = 4            # require we lived on the old side first
        min_confirm_bars = 4        # require persistence on the new side
        reentry_fail_bars = 6       # invalidate if we re-enter too quickly
        
        # Small percentage tolerance around the line to avoid micro flickers
        def is_above(idx: int, price_on_line: float) -> bool:
            tol = max(1e-12, 0.002 * closes[idx])  # ~0.2%
            return closes[idx] > price_on_line + tol
        
        def is_below(idx: int, price_on_line: float) -> bool:
            tol = max(1e-12, 0.002 * closes[idx])
            return closes[idx] < price_on_line - tol
        
        for trendline in existing_trendlines:
            trend_type = trendline.get('type', '')
            slope = trendline.get('slope', 0.0)
            intercept = trendline.get('intercept', 0.0)
            anchor_time = trendline.get('anchor_time_iso')
            
            if not anchor_time:
                continue
                
            try:
                t0 = datetime.fromisoformat(anchor_time.replace("Z", "+00:00"))
            except Exception:
                continue
            
            # Convert timestamps to hours since anchor
            ts_hours = [(t - t0).total_seconds() / 3600 for t in timestamps]
            
            # Project trendline to all timestamps
            projected_prices = [slope * h + intercept for h in ts_hours]
            
            # Check for trend changes based on trendline type
            if 'uptrend' in trend_type and 'lows' in trend_type:
                # Uptrend Low line: Look for 3 swing highs below the line (uptrend broken)
                crosses_below = []
                for i in swing_highs:
                    if is_below(i, projected_prices[i]):
                        crosses_below.append(i)
                
                if len(crosses_below) >= 3:
                    # Candidate break point
                    bp = min(crosses_below)
                    # Precondition: prior bars lived above the line (support held) before breaking below
                    pre_start = max(0, bp - min_pre_bars)
                    pre_ok = sum(1 for j in range(pre_start, bp) if not is_below(j, projected_prices[j])) >= max(1, min_pre_bars - 1)
                    # Confirmation: persist below for a few bars after break
                    confirm_end = min(len(closes), bp + min_confirm_bars)
                    confirm_ok = sum(1 for j in range(bp, confirm_end) if is_below(j, projected_prices[j])) >= max(1, min_confirm_bars - 1)
                    # Failure: quick re-entry above line within short window cancels
                    fail_end = min(len(closes), bp + reentry_fail_bars)
                    failed = any(not is_below(j, projected_prices[j]) for j in range(bp, fail_end)) and not confirm_ok
                    
                    if pre_ok and confirm_ok and not failed:
                        # Find the ATH (highest point) as the reversal point
                        ath_idx = max(swing_highs, key=lambda x: closes[x]) if swing_highs else bp
                        trend_changes.append({
                            'type': 'uptrend_to_downtrend',
                            'break_point': bp,
                            'reversal_point': ath_idx,
                            'trendline': trendline,
                            'crosses_count': len(crosses_below)
                        })
            
            elif 'downtrend' in trend_type and 'highs' in trend_type:
                # Downtrend High line: Look for 3 swing lows above the line (downtrend broken)
                crosses_above = []
                for i in swing_lows:
                    if is_above(i, projected_prices[i]):
                        crosses_above.append(i)
                
                if len(crosses_above) >= 3:
                    first_cross = min(crosses_above)
                    # Precondition: prior bars lived below the line (resistance held) before breaking above
                    pre_start = max(0, first_cross - min_pre_bars)
                    pre_ok = sum(1 for j in range(pre_start, first_cross) if not is_above(j, projected_prices[j])) >= max(1, min_pre_bars - 1)
                    # Confirmation: persist above for a few bars after break
                    confirm_end = min(len(closes), first_cross + min_confirm_bars)
                    confirm_ok = sum(1 for j in range(first_cross, confirm_end) if is_above(j, projected_prices[j])) >= max(1, min_confirm_bars - 1)
                    # Failure: quick re-entry below the line cancels
                    fail_end = min(len(closes), first_cross + reentry_fail_bars)
                    failed = any(not is_above(j, projected_prices[j]) for j in range(first_cross, fail_end)) and not confirm_ok
                    
                    if pre_ok and confirm_ok and not failed:
                        trend_changes.append({
                            'type': 'downtrend_to_uptrend',
                            'break_point': first_cross,
                            'reversal_point': first_cross,
                            'trendline': trendline,
                            'crosses_count': len(crosses_above)
                        })
        
        return trend_changes

    def _create_current_trend_lines(self, timestamps: List[datetime], closes: List[float], 
                                   swing_highs: List[int], swing_lows: List[int],
                                   trend_change: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create new trend lines from trend change point"""
        reversal_idx = trend_change['reversal_point']
        new_trend_type = 'downtrend' if trend_change['type'] == 'uptrend_to_downtrend' else 'uptrend'
        
        # Get swing points from reversal point onwards
        segment_highs = [i for i in swing_highs if i >= reversal_idx]
        segment_lows = [i for i in swing_lows if i >= reversal_idx]
        
        if len(segment_highs) < 2 and len(segment_lows) < 2:
            return []
        
        # Generate new trendlines for the current trend
        current_trendlines = self._generate_trendlines_for_segment(
            timestamps, closes, segment_highs, segment_lows, new_trend_type
        )
        
        # Add time-based scoring
        now = datetime.now(timezone.utc)
        reversal_time = timestamps[reversal_idx]
        age_hours = (now - reversal_time).total_seconds() / 3600
        
        for trendline in current_trendlines:
            # Add time-based strength (0.1 per hour)
            time_strength = age_hours * 0.1
            trendline['time_strength'] = time_strength
            trendline['age_hours'] = age_hours
            trendline['is_current'] = True
        
        return current_trendlines

    def _cluster_levels(self, closes: List[float], idxs: List[int], tol_percent: float) -> List[Dict[str, Any]]:
        """Cluster levels using percentage-based tolerance - sort by price first"""
        # Get all swing prices and sort by price (not time)
        swing_prices = [closes[i] for i in idxs]
        swing_prices.sort()  # Sort by price, not time
        
        centers: List[float] = []
        counts: List[int] = []
        
        for price in swing_prices:
            assigned = False
            for k, c in enumerate(centers):
                # Calculate percentage difference
                percent_diff = abs(price - c) / c
                if percent_diff <= tol_percent:
                    centers[k] = (centers[k] * counts[k] + price) / (counts[k] + 1)
                    counts[k] += 1
                    assigned = True
                    break
            if not assigned:
                centers.append(price)
                counts.append(1)
        
        scored = [
            {"price": centers[k], "strength": counts[k], "confidence": min(1.0, counts[k] / 10.0), "type": "line"} for k in range(len(centers))
        ]
        # Keep top 9 (balanced limit to capture important levels)
        scored.sort(key=lambda x: (x["strength"], -abs(x["price"])), reverse=True)
        return scored[:9]
    
    def _calculate_fibonacci_levels(self, ath_price: float, atl_price: float, current_price: float, existing_sr_levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate Fibonacci levels with S/R correlation bonuses"""
        fib_levels = []
        fib_range = ath_price - atl_price
        
        # Standard Fibonacci retracements (ATH to ATL)
        retracement_levels = [
            (0.0, "0% (ATH)", "fib_ath"),
            (0.236, "23.6%", "fib_236"),
            (0.382, "38.2%", "fib_382"),
            (0.5, "50%", "fib_50"),
            (0.618, "61.8%", "fib_618"),
            (0.786, "78.6%", "fib_786"),
            (1.0, "100% (ATL)", "fib_atl")
        ]
        
        # Fibonacci extensions (ATL to above ATH)
        extension_levels = [
            (1.272, "127.2%", "fib_ext_127"),
            (1.618, "161.8%", "fib_ext_162"),
            (2.0, "200%", "fib_ext_200"),
            (2.618, "261.8%", "fib_ext_262"),
            (3.0, "300%", "fib_ext_300"),
            (4.236, "423.6%", "fib_ext_424")
        ]
        
        # Calculate retracement levels
        for fib_pct, fib_name, fib_id in retracement_levels:
            fib_price = ath_price - (fib_pct * fib_range)
            strength, correlation = self._calculate_fib_strength(fib_price, existing_sr_levels)
            
            fib_levels.append({
                "price": fib_price,
                "strength": strength,
                "confidence": min(1.0, strength / 20.0),
                "type": "line",
                "source": "fib_retracement",
                "fib_level": fib_name,
                "fib_id": fib_id,
                "correlation": correlation
            })
        
        # Calculate extension levels (only above current price for take profit targets)
        for fib_pct, fib_name, fib_id in extension_levels:
            fib_price = atl_price + (fib_pct * fib_range)
            
            # Only include extensions above current price
            if fib_price > current_price:
                strength, correlation = self._calculate_fib_strength(fib_price, existing_sr_levels)
                
                fib_levels.append({
                    "price": fib_price,
                    "strength": strength,
                    "confidence": min(1.0, strength / 20.0),
                    "type": "line",
                    "source": "fib_extension",
                    "fib_level": fib_name,
                    "fib_id": fib_id,
                    "correlation": correlation,
                    "take_profit_target": True
                })
        
        return fib_levels
    
    def _calculate_fib_strength(self, fib_price: float, existing_sr_levels: List[Dict[str, Any]]) -> tuple:
        """Calculate Fibonacci level strength based on S/R correlation"""
        base_strength = 15  # Base strength for Fibonacci levels
        
        # Find closest existing S/R level
        closest_level = None
        min_diff = float('inf')
        
        for sr_level in existing_sr_levels:
            diff = abs(sr_level['price'] - fib_price)
            if diff < min_diff:
                min_diff = diff
                closest_level = sr_level
        
        if closest_level:
            # Calculate correlation bonus
            diff_pct = (min_diff / fib_price) * 100
            
            if diff_pct < 3.0:
                # High correlation - add full S/R strength
                correlation_bonus = closest_level['strength']
                correlation = "HIGH"
            elif diff_pct < 7.0:
                # Medium correlation - add half S/R strength
                correlation_bonus = closest_level['strength'] // 2
                correlation = "MEDIUM"
            else:
                # Low correlation - no bonus
                correlation_bonus = 0
                correlation = "LOW"
            
            total_strength = base_strength + correlation_bonus
        else:
            # No S/R correlation
            total_strength = base_strength
            correlation = "NONE"
        
        return total_strength, correlation
    
    def _get_token_name(self, contract: str, chain: str) -> Optional[str]:
        """Get token name from database if available"""
        try:
            # Try to get token ticker from positions table
            result = self.sb.table("lowcap_positions").select("token_ticker").eq("token_contract", contract).eq("token_chain", chain).limit(1).execute()
            if result.data and result.data[0].get('token_ticker'):
                return result.data[0]['token_ticker']
        except Exception:
            pass
        return None
    
    def _create_sr_zones(self, levels: List[Dict[str, Any]], zone_threshold: float = 0.03) -> List[Dict[str, Any]]:
        """Create S/R zones by merging nearby levels within threshold"""
        if len(levels) < 2:
            return levels
        
        # Sort levels by price
        sorted_levels = sorted(levels, key=lambda x: x['price'])
        zones = []
        current_zone = [sorted_levels[0]]
        
        for i in range(1, len(sorted_levels)):
            level = sorted_levels[i]
            prev_level = current_zone[-1]
            
            # Check if within threshold (percentage)
            price_diff = abs(level['price'] - prev_level['price']) / prev_level['price']
            
            if price_diff <= zone_threshold and len(current_zone) < 3:
                # Add to current zone
                current_zone.append(level)
            else:
                # Finalize current zone and start new one
                if len(current_zone) > 1:
                    # Create zone from multiple levels
                    zone_price_min = min(l['price'] for l in current_zone)
                    zone_price_max = max(l['price'] for l in current_zone)
                    zone_touches = sum(l['strength'] for l in current_zone)
                    zones.append({
                        'type': 'zone',
                        'price_min': zone_price_min,
                        'price_max': zone_price_max,
                        'touches': zone_touches,
                        'strength': zone_touches,  # Add strength for compatibility
                        'levels': len(current_zone)
                    })
                else:
                    # Single level
                    zones.append({
                        'type': 'line',
                        'price': current_zone[0]['price'],
                        'touches': current_zone[0]['strength'],
                        'strength': current_zone[0]['strength']  # Add strength for compatibility
                    })
                
                current_zone = [level]
        
        # Handle final zone
        if len(current_zone) > 1:
            zone_price_min = min(l['price'] for l in current_zone)
            zone_price_max = max(l['price'] for l in current_zone)
            zone_touches = sum(l['strength'] for l in current_zone)
            zones.append({
                'type': 'zone',
                'price_min': zone_price_min,
                'price_max': zone_price_max,
                'touches': zone_touches,
                'strength': zone_touches,  # Add strength for compatibility
                'levels': len(current_zone)
            })
        else:
            zones.append({
                'type': 'line',
                'price': current_zone[0]['price'],
                'touches': current_zone[0]['strength'],
                'strength': current_zone[0]['strength']  # Add strength for compatibility
            })
        
        return zones

    def _fit_theil_sen(self, xs: List[float], ys: List[float]) -> Tuple[float, float]:
        # Minimal Theil–Sen: median of pairwise slopes
        if len(xs) < 3:
            return (0.0, ys[-1] if ys else 0.0)
        slopes = []
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                dx = xs[j] - xs[i]
                if dx == 0:
                    continue
                slopes.append((ys[j] - ys[i]) / dx)
        m = median(slopes) if slopes else 0.0
        # Intercept via median of (y - m x)
        intercepts = [ys[i] - m * xs[i] for i in range(len(xs))]
        b = median(intercepts) if intercepts else (ys[-1] if ys else 0.0)
        return m, b

    def _cluster_swing_points(self, timestamps: List[datetime], closes: List[float], 
                             swing_indices: List[int], cluster_window_hours: int = 24, 
                             price_threshold_pct: float = 10.0) -> List[List[int]]:
        """Cluster swing points by both time and price proximity"""
        if len(swing_indices) < 2:
            return [swing_indices] if swing_indices else []
        
        # Sort swing points by timestamp
        sorted_swings = sorted(swing_indices, key=lambda i: timestamps[i])
        
        clusters = []
        current_cluster = [sorted_swings[0]]
        
        for i in range(1, len(sorted_swings)):
            current_idx = sorted_swings[i]
            prev_idx = sorted_swings[i-1]
            
            # Calculate time difference in hours
            time_diff_hours = (timestamps[current_idx] - timestamps[prev_idx]).total_seconds() / 3600
            
            # Calculate price difference as percentage
            current_price = closes[current_idx]
            prev_price = closes[prev_idx]
            price_diff_pct = abs(current_price - prev_price) / prev_price * 100 if prev_price > 0 else 0
            
            # Check both time AND price proximity
            if time_diff_hours <= cluster_window_hours and price_diff_pct <= price_threshold_pct:
                # Add to current cluster (close in both time and price)
                current_cluster.append(current_idx)
            else:
                # Start new cluster
                if len(current_cluster) >= 3:  # Only keep clusters with 3+ points
                    clusters.append(current_cluster)
                current_cluster = [current_idx]
        
        # Add the last cluster
        if len(current_cluster) >= 3:
            clusters.append(current_cluster)
        
        return clusters

    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return []
        
        ema_values = []
        multiplier = 2 / (period + 1)
        
        # Start with SMA for the first value
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        
        # Calculate EMA for remaining values
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        # Pad the beginning with None values to match original length
        return [None] * (period - 1) + ema_values

    def _calculate_avwap(self, prices: List[float], volumes: List[float], window: int = None) -> List[float]:
        """Calculate Anchored Volume-Weighted Average Price (AVWAP)"""
        if len(prices) < 2 or len(volumes) < 2:
            return []
        
        avwap_values = []
        
        # If window is None, calculate cumulative AVWAP from start
        # Otherwise use rolling window
        if window is None:
            # Cumulative AVWAP from beginning
            cumulative_pv = 0.0
            cumulative_v = 0.0
            
            for i in range(len(prices)):
                if volumes[i] > 0:
                    cumulative_pv += prices[i] * volumes[i]
                    cumulative_v += volumes[i]
                    avwap = cumulative_pv / cumulative_v if cumulative_v > 0 else prices[i]
                else:
                    # Use previous AVWAP if no volume
                    avwap = avwap_values[-1] if avwap_values else prices[i]
                avwap_values.append(avwap)
        else:
            # Rolling window AVWAP
            for i in range(len(prices)):
                start_idx = max(0, i - window + 1)
                window_prices = prices[start_idx:i+1]
                window_volumes = volumes[start_idx:i+1]
                
                pv_sum = sum(p * v for p, v in zip(window_prices, window_volumes) if v > 0)
                v_sum = sum(v for v in window_volumes if v > 0)
                
                if v_sum > 0:
                    avwap = pv_sum / v_sum
                else:
                    avwap = prices[i] if prices else 0.0
                
                avwap_values.append(avwap)
        
        return avwap_values

    def _generate_trendlines_for_segment(self, timestamps: List[datetime], closes: List[float], 
                                       swing_highs: List[int], swing_lows: List[int], 
                                       segment_name: str) -> List[Dict[str, Any]]:
        """Generate trendlines for a specific trend segment using clustered swing points"""
        trendlines = []
        
        if len(swing_highs) < 2 and len(swing_lows) < 2:
            return trendlines
        
        # Convert timestamps to numeric for regression
        ts_numeric = [(t - timestamps[0]).total_seconds() / 3600 for t in timestamps]
        
        # Cluster swing highs and collect all "good" swing points
        if len(swing_highs) >= 2:
            high_clusters = self._cluster_swing_points(timestamps, closes, swing_highs, cluster_window_hours=24, price_threshold_pct=10.0)
            
            # Collect all swing points that belong to clusters of 3+ points
            good_high_indices = []
            for cluster in high_clusters:
                good_high_indices.extend(cluster)
            
            # Draw ONE trendline through all good swing highs
            if len(good_high_indices) >= 2:
                high_times = [ts_numeric[i] for i in good_high_indices]
                high_prices = [closes[i] for i in good_high_indices]
                
                # Linear regression for all good swing highs
                n = len(high_times)
                sum_x = sum(high_times)
                sum_y = sum(high_prices)
                sum_xy = sum(high_times[i] * high_prices[i] for i in range(n))
                sum_x2 = sum(t * t for t in high_times)
                
                if n * sum_x2 - sum_x * sum_x != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                    intercept = (sum_y - slope * sum_x) / n
                    
                    # Calculate R² score
                    y_pred = [slope * t + intercept for t in high_times]
                    ss_res = sum((high_prices[i] - y_pred[i]) ** 2 for i in range(n))
                    ss_tot = sum((p - sum_y/n) ** 2 for p in high_prices)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                    
                    trendlines.append({
                        "type": f"{segment_name}_highs",
                        "slope": slope,
                        "intercept": intercept,
                        "r2_score": r2,
                        "points_count": len(good_high_indices),
                        "confidence": min(1.0, r2),
                        "anchor_time_iso": timestamps[0].isoformat()
                    })
        
        # Cluster swing lows and collect all "good" swing points
        if len(swing_lows) >= 2:
            low_clusters = self._cluster_swing_points(timestamps, closes, swing_lows, cluster_window_hours=24, price_threshold_pct=10.0)
            
            # Collect all swing points that belong to clusters of 3+ points
            good_low_indices = []
            for cluster in low_clusters:
                good_low_indices.extend(cluster)
            
            # Draw ONE trendline through all good swing lows
            if len(good_low_indices) >= 2:
                low_times = [ts_numeric[i] for i in good_low_indices]
                low_prices = [closes[i] for i in good_low_indices]
                
                # Linear regression for all good swing lows
                n = len(low_times)
                sum_x = sum(low_times)
                sum_y = sum(low_prices)
                sum_xy = sum(low_times[i] * low_prices[i] for i in range(n))
                sum_x2 = sum(t * t for t in low_times)
                
                if n * sum_x2 - sum_x * sum_x != 0:
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                    intercept = (sum_y - slope * sum_x) / n
                    
                    # Calculate R² score
                    y_pred = [slope * t + intercept for t in low_times]
                    ss_res = sum((low_prices[i] - y_pred[i]) ** 2 for i in range(n))
                    ss_tot = sum((p - sum_y/n) ** 2 for p in low_prices)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                    
                    trendlines.append({
                        "type": f"{segment_name}_lows",
                        "slope": slope,
                        "intercept": intercept,
                        "r2_score": r2,
                        "points_count": len(good_low_indices),
                        "confidence": min(1.0, r2),
                        "anchor_time_iso": timestamps[0].isoformat()
                    })
        
        return trendlines

    def build(self) -> int:
        now = datetime.now(timezone.utc)
        minutes = self.lookback_days * 24 * 60
        positions = self._active_positions()
        updated = 0
        
        for p in positions:
            pid = p["id"]
            contract = p["token_contract"]
            chain = p["token_chain"]
            bars = self._fetch_bars(contract, chain, now, None)  # Use all available data
            
            if len(bars) < 50:  # Need sufficient data for analysis
                continue
                
            closes = [float(b["close_usd"]) for b in bars]
            highs = [float(b.get("high_usd", b["close_usd"])) for b in bars]
            lows = [float(b.get("low_usd", b["close_usd"])) for b in bars]
            timestamps = [datetime.fromisoformat(b["timestamp"].replace('Z', '+00:00')) for b in bars]
            
            # Use improved percentage-based swing detection
            swing_highs, swing_lows = self._swings_percentage_based(closes, prominence_threshold=0.5)
            
            # Get swing points with coordinates
            swing_points = self._get_swing_points_with_coordinates(timestamps, highs, lows, closes)
            
            if len(swing_highs) < 3 and len(swing_lows) < 3:
                continue  # Need sufficient swing points
            
            # Generate horizontal S/R levels (combine all swing points)
            all_swing_points = swing_highs + swing_lows
            sr_levels = self._cluster_levels(closes, all_swing_points, tol_percent=0.06)  # Use 6% tolerance for native prices
            
            # Add ATH and ATL as important S/R levels
            if len(closes) > 0:
                ath_price = max(closes)
                atl_price = min(closes)
                current_price = closes[-1]
                
                # Add ATH level
                sr_levels.append({
                    "price": ath_price,
                    "strength": 10,  # High strength for ATH
                    "confidence": 1.0,
                    "type": "line",
                    "touches": 1,
                    "source": "ATH"
                })
                
                # Add ATL level  
                sr_levels.append({
                    "price": atl_price,
                    "strength": 10,  # High strength for ATL
                    "confidence": 1.0,
                    "type": "line", 
                    "touches": 1,
                    "source": "ATL"
                })
                
                # Add Fibonacci levels with S/R correlation bonuses
                fib_levels = self._calculate_fibonacci_levels(ath_price, atl_price, current_price, sr_levels)
                sr_levels.extend(fib_levels)
                
                # Sort by strength and keep top levels
                sr_levels.sort(key=lambda x: (x["strength"], -abs(x["price"])), reverse=True)
                sr_levels = sr_levels[:12]  # Keep top 12 levels (increased for Fib levels)
            
            # Use proper trend detection instead of the broken ATH/ATL logic
            trend_segments = self._detect_trends_proper(timestamps, closes, highs, lows)
            
            # Generate trendlines for each sustained trend segment
            all_trendlines = []
            segment_trendlines_list: List[List[Dict[str, Any]]] = []
            
            for segment in trend_segments:
                # Get swing points within this segment
                segment_highs = []
                segment_lows = []
                
                for i in swing_highs:
                    if segment['start']['timestamp'] <= timestamps[i] <= segment['end']['timestamp']:
                        segment_highs.append(i)
                
                for i in swing_lows:
                    if segment['start']['timestamp'] <= timestamps[i] <= segment['end']['timestamp']:
                        segment_lows.append(i)
                
                # Generate trendlines for this segment
                if len(segment_highs) >= 2 or len(segment_lows) >= 2:
                    segment_trendlines = self._generate_trendlines_for_segment(
                        timestamps, closes, segment_highs, segment_lows, segment['type']
                    )
                    all_trendlines.extend(segment_trendlines)
                    segment_trendlines_list.append(segment_trendlines)
                else:
                    segment_trendlines_list.append([])
            
            # If no segments found, analyze full dataset
            if not trend_segments and (len(swing_highs) >= 2 or len(swing_lows) >= 2):
                full_trendlines = self._generate_trendlines_for_segment(
                    timestamps, closes, swing_highs, swing_lows, "full"
                )
                all_trendlines.extend(full_trendlines)
            
            # Determine current trend from last segment
            current_trend_type = trend_segments[-1].get('type') if trend_segments else None
            attempt: Dict[str, Any] | None = None
            last_change: Dict[str, Any] | None = None

            # Convert trendlines to the expected format and build LLM payload
            diagonals: Dict[str, Any] = {}
            llm_trendlines: List[Dict[str, Any]] = []
            current_price = closes[-1]

            # Helper to get time range labels for LLM
            def time_range_for(indices: List[int]) -> str:
                if not indices:
                    return ""
                start = timestamps[min(indices)].strftime("%m-%d")
                end = timestamps[max(indices)].strftime("%m-%d")
                return f"{start}–{end}"

            for i, trendline in enumerate(all_trendlines):
                name_key = f"{trendline['type']}_{i+1}"
                diagonals[name_key] = {
                    "type": trendline["type"],
                    "slope": trendline["slope"],
                    "intercept": trendline["intercept"],
                    "r2_score": trendline["r2_score"],
                    "points_count": trendline["points_count"],
                    "confidence": trendline["confidence"],
                    # Anchor time used for regression baseline (time=0)
                    "anchor_time_iso": timestamps[0].isoformat(),
                }

                # Derive human-readable name and time range
                ttype: str = trendline["type"]
                if ttype.startswith("uptrend_"):
                    hr_name = "Uptrend " + ("Resistance" if ttype.endswith("highs") else "Support")
                elif ttype.startswith("downtrend_"):
                    hr_name = "Downtrend " + ("Resistance" if ttype.endswith("highs") else "Support")
                else:
                    hr_name = "Trendline"

                # Rough time ranges by splitting at detected change_time above
                if 'uptrend' in ttype and 'change_time' in locals():
                    trange = f"{timestamps[0].strftime('%m-%d')}–{change_time.strftime('%m-%d')}"
                elif 'downtrend' in ttype and 'change_time' in locals():
                    trange = f"{change_time.strftime('%m-%d')}–{timestamps[-1].strftime('%m-%d')}"
                else:
                    trange = f"{timestamps[0].strftime('%m-%d')}–{timestamps[-1].strftime('%m-%d')}"

                llm_trendlines.append({
                    "name": hr_name,
                    "type": ttype,
                    "slope": trendline["slope"],
                    "r2_score": trendline["r2_score"],
                    "points_count": trendline["points_count"],
                    "time_range": trange,
                    "description": "Auto-detected diagonal for segment",
                })

            # Render diagonals-only chart (using our proven approach)
            if not self.generate_charts:
                out_png = ""
            else:
                try:
                    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1]})
                    
                    # Price chart
                    # Get token name if available, otherwise use contract
                    token_name = self._get_token_name(contract, chain) or f'Token_{contract[:8]}'
                    
                    ax1.plot(timestamps, closes, 'b-', linewidth=1, label=f'{token_name} Price (Native)', alpha=0.8)
                    
                    # Get volumes for AVWAP calculation
                    volumes = [float(b["volume"]) for b in bars]
                    
                    # Calculate EMAs for bands
                    ema20 = self._calculate_ema(closes, 20)
                    ema60 = self._calculate_ema(closes, 60)
                    ema144 = self._calculate_ema(closes, 144)
                    ema250 = self._calculate_ema(closes, 250)
                    ema333 = self._calculate_ema(closes, 333)
                    
                    # Calculate AVWAP (cumulative from start)
                    avwap = self._calculate_avwap(closes, volumes, window=None)
                    
                    # Plot fast band: AVWAP + EMA 20
                    if avwap and len(avwap) > 0:
                        # Filter out None values for plotting
                        avwap_valid = [(t, v) for t, v in zip(timestamps, avwap) if v is not None]
                        if avwap_valid:
                            avwap_times, avwap_values = zip(*avwap_valid)
                            ax1.plot(avwap_times, avwap_values, 'cyan', linewidth=2, label='AVWAP', alpha=0.8, linestyle='--')
                    if ema20:
                        ax1.plot(timestamps, ema20, 'orange', linewidth=2, label='EMA 20', alpha=0.8)
                    
                    # Plot mid band: EMA 60 - EMA 144
                    if ema60:
                        ax1.plot(timestamps, ema60, 'purple', linewidth=2, label='EMA 60', alpha=0.8)
                    if ema144:
                        ax1.plot(timestamps, ema144, 'red', linewidth=2, label='EMA 144', alpha=0.8)
                    
                    # Plot slow band: EMA 250 - EMA 333
                    if ema250:
                        ax1.plot(timestamps, ema250, 'darkred', linewidth=2, label='EMA 250', alpha=0.8)
                    if ema333:
                        ax1.plot(timestamps, ema333, 'black', linewidth=3, label='EMA 333', alpha=0.9)
                    
                    # Determine band states at latest bar
                    latest_idx = len(closes) - 1
                    band_states = {}
                    
                    # Fast band: EMA 20 vs AVWAP
                    if ema20 and avwap and latest_idx < len(ema20) and latest_idx < len(avwap):
                        if ema20[latest_idx] is not None and avwap[latest_idx] is not None:
                            fast_bullish = ema20[latest_idx] > avwap[latest_idx]
                            band_states['fast'] = 'bullish' if fast_bullish else 'bearish'
                    
                    # Mid band: EMA 60 vs EMA 144
                    if ema60 and ema144 and latest_idx < len(ema60) and latest_idx < len(ema144):
                        if ema60[latest_idx] is not None and ema144[latest_idx] is not None:
                            mid_bullish = ema60[latest_idx] > ema144[latest_idx]
                            band_states['mid'] = 'bullish' if mid_bullish else 'bearish'
                    
                    # Slow band: EMA 250 vs EMA 333
                    if ema250 and ema333 and latest_idx < len(ema250) and latest_idx < len(ema333):
                        if ema250[latest_idx] is not None and ema333[latest_idx] is not None:
                            slow_bullish = ema250[latest_idx] > ema333[latest_idx]
                            band_states['slow'] = 'bullish' if slow_bullish else 'bearish'
                    
                    # Add band state annotation
                    if band_states:
                        band_text = []
                        for band_name, state in band_states.items():
                            symbol = 'UP' if state == 'bullish' else 'DOWN'
                            color = 'green' if state == 'bullish' else 'red'
                            band_text.append(f'{band_name.upper()}: {symbol}')
                    
                    if band_text:
                        # Determine overall trend color
                        all_bullish = all(s == 'bullish' for s in band_states.values())
                        all_bearish = all(s == 'bearish' for s in band_states.values())
                        bg_color = 'lightgreen' if all_bullish else ('lightcoral' if all_bearish else 'lightyellow')
                        
                        ax1.text(0.02, 0.98, ' | '.join(band_text), transform=ax1.transAxes,
                                fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', 
                                facecolor=bg_color, alpha=0.8))
                    
                    ax1.set_ylabel('Price (Native)')
                    ax1.set_title(f'{token_name} Diagonals + EMAs - Analysis Chart')
                    ax1.grid(True, alpha=0.3)
                    
                    # Mark swing highs and lows
                    swing_high_times = [timestamps[i] for i in swing_highs]
                    swing_high_prices = [closes[i] for i in swing_highs]
                    ax1.scatter(swing_high_times, swing_high_prices, color='red', s=80, marker='^', 
                           label=f'Swing Highs ({len(swing_highs)})', alpha=0.8, zorder=5)
                    
                    swing_low_times = [timestamps[i] for i in swing_lows]
                    swing_low_prices = [closes[i] for i in swing_lows]
                    ax1.scatter(swing_low_times, swing_low_prices, color='green', s=80, marker='v', 
                           label=f'Swing Lows ({len(swing_lows)})', alpha=0.8, zorder=5)
                    
                    # Add ATH/ATL pivot lines and trend segments
                    if trend_segments:
                        for i, segment in enumerate(trend_segments):
                            # Mark segment start and end
                            ax1.axvline(x=segment['start']['timestamp'], color='purple', linestyle=':', alpha=0.6, linewidth=1)
                            ax1.axvline(x=segment['end']['timestamp'], color='red', linestyle=':', alpha=0.6, linewidth=1)
                            
                            # Add segment labels
                            mid_time = segment['start']['timestamp'] + (segment['end']['timestamp'] - segment['start']['timestamp']) / 2
                            ax1.text(mid_time, max(closes) * 0.9, f"{segment['name']}\n({segment['type']})", 
                                    ha='center', va='center', fontsize=8, alpha=0.8,
                                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))
                    
                    # Plot trendlines with specific colors for better visibility
                    def get_trendline_color(trendline_type: str) -> str:
                        """Assign specific colors based on trendline type for better visibility"""
                        if 'uptrend' in trendline_type.lower() and 'highs' in trendline_type.lower():
                            return 'purple'  # Uptrend highs - purple
                        elif 'uptrend' in trendline_type.lower() and 'lows' in trendline_type.lower():
                            return 'green'  # Uptrend lows - green
                        elif 'downtrend' in trendline_type.lower() and 'highs' in trendline_type.lower():
                            return 'red'    # Downtrend highs - red
                        elif 'downtrend' in trendline_type.lower() and 'lows' in trendline_type.lower():
                            return 'orange' # Downtrend lows - orange
                        else:
                            return 'blue'  # Default - blue
                    
                    def get_trendline_style(trendline_type: str) -> str:
                        """Assign specific line styles based on trendline type"""
                        if 'highs' in trendline_type.lower():
                            return '-'     # Solid for highs
                        else:
                            return '--'    # Dashed for lows
                    
                    for i, trendline in enumerate(all_trendlines):
                        # Convert timestamps to numeric for regression
                        ts_numeric = [(t - timestamps[0]).total_seconds() / 3600 for t in timestamps]
                        
                        # Extend line to chart edges
                        time_start = (timestamps[0] - timestamps[0]).total_seconds() / 3600
                        time_end = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
                        price_start = trendline["slope"] * time_start + trendline["intercept"]
                        price_end = trendline["slope"] * time_end + trendline["intercept"]
                        
                        color = get_trendline_color(trendline["type"])
                        style = get_trendline_style(trendline["type"])
                        
                        ax1.plot([timestamps[0], timestamps[-1]], [price_start, price_end], 
                                color=color, linestyle=style, linewidth=2, 
                                label=f'{trendline["type"].replace("_", " ").title()} (R²={trendline["r2_score"]:.3f})', alpha=0.8)
                    
                    # Add horizontal S/R levels to the chart (exclude Fib extensions for clarity)
                    for level in sr_levels:
                        # Skip Fib extensions on chart (too cluttered) but keep in data
                        if level.get('source') == 'fib_extension':
                            continue
                            
                        ax1.axhline(y=level['price'], color='blue', linestyle='-', alpha=0.6, linewidth=1)
                        source = level.get('source', 'clustered')
                        label = f"{source}: {level['price']:.6f} ({level['strength']})"
                        ax1.text(timestamps[0], level['price'], label, 
                                fontsize=8, color='blue', alpha=0.8, va='bottom')

                    # Mark the most recent confirmed trend change on chart
                    try:
                        if last_change:
                            from datetime import datetime as _dt
                            def _to_utc_dt(s: str) -> datetime:
                                # Parse ISO string and normalize to UTC-aware
                                try:
                                    dt = _dt.fromisoformat(s.replace('Z', '+00:00'))
                                    if dt.tzinfo is None:
                                        return dt.replace(tzinfo=timezone.utc)
                                    return dt.astimezone(timezone.utc)
                                except Exception:
                                    return timestamps[0]

                            change_dir = last_change.get('direction')
                            ts_prev_end = _to_utc_dt(last_change.get('end_at_previous')) if last_change.get('end_at_previous') else None
                            ts_start = _to_utc_dt(last_change.get('start_at')) if last_change.get('start_at') else None
                            ts_confirm = _to_utc_dt(last_change.get('confirmed_at')) if last_change.get('confirmed_at') else None

                            ymax = max(closes) if closes else 0.0

                            if ts_prev_end:
                                ax1.axvline(ts_prev_end, color='purple', linestyle=':', linewidth=1.5, alpha=0.9, label='Prev trend end (ATH/ATL)')
                            if ts_start and change_dir == 'down_to_up':
                                ax1.axvline(ts_start, color='green', linestyle='--', linewidth=1.5, alpha=0.9, label='Break (Uptrend start)')
                            # Only draw confirmation if it occurs after previous trend end
                            if ts_confirm and (not ts_prev_end or ts_confirm > ts_prev_end):
                                ax1.axvline(ts_confirm, color='black', linestyle='-', linewidth=1.2, alpha=0.9, label='Trend change confirmed')
                            # Annotate ISO times for debugging/clarity
                            y_annot = ymax * 1.02 if ymax else 0.0
                            x0 = ts_prev_end or timestamps[0]
                            lbl = []
                            if ts_prev_end:
                                lbl.append(f"prev_end={ts_prev_end.isoformat()}")
                            if ts_start and change_dir == 'down_to_up':
                                lbl.append(f"break={ts_start.isoformat()}")
                            if ts_confirm:
                                lbl.append(f"confirm={ts_confirm.isoformat()}")
                            if lbl:
                                ax1.text(x0, closes[-1] if closes else 0.0, " | ".join(lbl), fontsize=8, color='black', alpha=0.8, va='bottom')
                    except Exception:
                        pass
                    
                    ax1.legend()
                    
                    # Set chart limits to focus on relevant data (reduce zoom out)
                    if len(timestamps) > 0:
                        # Focus on the main data range, with some padding
                        time_padding = (timestamps[-1] - timestamps[0]) * 0.05  # 5% padding
                        ax1.set_xlim(timestamps[0] - time_padding, timestamps[-1] + time_padding)
                        
                        # Price limits with some padding
                        price_padding = (max(closes) - min(closes)) * 0.1  # 10% padding
                        ax1.set_ylim(min(closes) - price_padding, max(closes) + price_padding)
                    
                    # Volume chart - use appropriate width for timeframe-specific bars
                    volumes = [float(b["volume"]) for b in bars]
                    # Calculate appropriate width based on timeframe
                    bar_width_map = {"1m": 1/1440, "15m": 1/96, "1h": 1/24, "4h": 1/6}  # Fraction of a day
                    bar_width = bar_width_map.get(self.timeframe, 1/24)  # Default to 1h if unknown
                    ax2.bar(timestamps, volumes, width=bar_width, alpha=0.7, color='gray')
                    ax2.set_ylabel('Volume (USD)')
                    ax2.set_xlabel('Time')
                    ax2.grid(True, alpha=0.3)
                    
                    # Format x-axis
                    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                    
                    plt.xticks(rotation=45)
                    plt.draw()  # Draw figure before tight_layout to ensure all axes are rendered
                    plt.tight_layout()
                    
                    # Use token name for file naming (token_name already defined above)
                    safe_name = token_name.replace(' ', '_').replace('/', '_')
                    out_png = f"diagonals_{safe_name}_{chain}_{now.strftime('%Y%m%d%H%M')}.png"
                    plt.savefig(out_png, dpi=300, bbox_inches='tight')
                    plt.close(fig)
                except Exception as _e:
                    out_png = ""
                    logger.warning("Failed to render diagonals chart: %s", _e)

            # LLM call removed - algorithmic approach is now sufficient

            # --- Normalize SR levels for SM consumption ---
            def _round_native(px: float) -> Tuple[float, int]:
                """Return (rounded_price, decimals_used) for stable IDs and comparisons."""
                if px >= 1.0:
                    n = 6
                elif px >= 0.01:
                    n = 8
                else:
                    n = 10
                return (round(px, n), n)

            def _stable_level_id(chain: str, contract: str, source: str, price_rounded: float, decimals: int) -> str:
                base = f"{chain}:{contract}:{source}:{price_rounded:.{decimals}f}"
                # Simple, deterministic short hash for ID stability
                import hashlib
                return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

            # Ensure levels list exists
            sr_levels = sr_levels or []

            # Sort by price descending for engine consumption
            sr_levels.sort(key=lambda x: float(x.get("price", 0.0)), reverse=True)

            # Enrich each level with id, native rounding, explicit order
            for idx, lvl in enumerate(sr_levels):
                try:
                    price_native = float(lvl.get("price", 0.0))
                except Exception:
                    price_native = 0.0
                price_rounded, decs = _round_native(price_native)
                source = str(lvl.get("source") or lvl.get("type") or "clustered")
                lvl["price_native_raw"] = price_native
                lvl["price_rounded_native"] = price_rounded
                lvl["order_desc"] = idx  # 0 = highest price
                lvl["id"] = _stable_level_id(chain, contract, source, price_rounded, decs)

            geometry = {
                "levels": {"sr_levels": sr_levels},
                "diagonals": diagonals,
                "trend_segments": len(trend_segments) if trend_segments else 0,
                "swing_points": {
                    "highs": len(swing_highs),
                    "lows": len(swing_lows),
                    "coordinates": swing_points  # Store actual swing point coordinates
                },
                "current_trend": {
                    "has_current": current_trend_type is not None,
                    "trend_type": current_trend_type,
                    "lines_count": 0
                },
                "attempt": attempt,
                "last_change": last_change,
                "updated_at": now.isoformat(),
            }
            
            self.persist.write_features_token_geometry(pid, geometry)
            updated += 1
            
        logger.info("Geometry built for %d positions", updated)
        return updated


def main(timeframe: str = "1h") -> None:
    """
    Main entry point for Geometry Builder.
    
    Args:
        timeframe: Timeframe to process ("1m", "15m", "1h", "4h")
    """
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    job = GeometryBuilder(timeframe=timeframe)
    job.build()


if __name__ == "__main__":
    main()


