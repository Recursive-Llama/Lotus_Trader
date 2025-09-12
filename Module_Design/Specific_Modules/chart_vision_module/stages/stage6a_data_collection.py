#!/usr/bin/env python3
"""
Stage 6A: Data Collection & Analysis

Processes Stage 5A consolidated results and generates structured analysis data
for Stage 6B. Focuses on code-based calculations with LLM integration for
pattern classification.

Input: Stage 5A consolidated results (JSON)
Output: Structured analysis data (JSON)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Stage6ADataCollector:
    """Stage 6A: Data Collection & Analysis"""
    
    def __init__(self, stage5a_results: Dict[str, Any]):
        self.stage5a_data = stage5a_results
        self.chart_data = stage5a_results.get('chart_data', {})
        self.elements = self.chart_data.get('elements', {})
        self.ohlc_data = self.chart_data.get('ohlc_data', {})
        self.calibration = self.chart_data.get('calibration', {})
        
        # Current price (latest OHLC close)
        self.current_price = self._get_current_price()
        
        # Cache for diagonal "now" prices
        self._diag_now_cache = {}
        
        # Missing data flags
        self.missing_data = []
        
    def _get_current_price(self) -> float:
        """Get current price from latest OHLC data"""
        ohlcv = self.ohlc_data.get('ohlcv', [])
        if not ohlcv:
            self.missing_data.append("ohlc_data.ohlcv")
            return 0.0
        
        # Latest candle close price
        latest_candle = ohlcv[-1]
        return latest_candle[4]  # Close price
    
    def calculate_diagonal_price_at_time(self, element: Dict[str, Any], timestamp: int) -> float:
        """Calculate diagonal line price at a specific timestamp with edge case guards"""
        pts = element.get('price_time_points', [])
        if len(pts) == 0:
            return 0.0
        if len(pts) == 1:
            return float(pts[0][1])

        ts = timestamp / 1000 if timestamp > 1e10 else timestamp
        # ensure sorted
        pts = sorted(pts, key=lambda p: p[0])

        for (t1, p1), (t2, p2) in zip(pts, pts[1:]):
            if t1 <= ts <= t2:
                dt = (t2 - t1) or 1e-9
                return p1 + (ts - t1) * (p2 - p1) / dt

        # extrapolate
        (t1, p1), (t2, p2) = pts[:2]
        if ts < t1:
            dt = (t2 - t1) or 1e-9
            return p1 + (ts - t1) * (p2 - p1) / dt
        (t1, p1), (t2, p2) = pts[-2:]
        dt = (t2 - t1) or 1e-9
        return p2 + (ts - t2) * (p2 - p1) / dt
    
    def analyze_element_sequence(self, element_id: str, element: Dict[str, Any], ohlcv: List[List]) -> Dict[str, Any]:
        """Analyze the sequence of events for a single element with proper state transitions"""
        element_type = element.get('element_type', '')
        
        events = []
        current_state = "unknown"
        touch_count = 0
        
        # Focus on recent events (last 50 candles for high-level, last 20 for detailed)
        recent_candles = ohlcv[-50:] if len(ohlcv) >= 50 else ohlcv
        
        if element_type == 'horizontal_line':
            line_price = element.get('price', 0.0)
            if line_price == 0:
                return {"error": "No price data for horizontal line"}
            
            # Analyze recent candles with proper state transitions
            for i, candle in enumerate(recent_candles):
                timestamp, open_price, high, low, close, volume = candle
                date = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d')
                
                # Determine current state
                curr_above = close > line_price
                prev_above = events[-1]['state'] == 'above' if events else None
                
                # Check for bounce (wick below level, close above)
                if curr_above and low < line_price:
                    bounce_amount = close - low
                    touch_count += 1
                    events.append({
                        'date': date,
                        'state': 'above',
                        'close': close,
                        'volume': volume,
                        'event': 'bounce',
                        'bounce_amount': bounce_amount,
                        'touch_count': touch_count,
                        'candle_index': len(ohlcv) - len(recent_candles) + i
                    })
                # State transition: below → above
                elif curr_above and prev_above is False:
                    bounce_amount = close - low
                    touch_count = 0  # Reset counter
                    events.append({
                        'date': date,
                        'state': 'above',
                        'close': close,
                        'volume': volume,
                        'event': 'reclaim',
                        'bounce_amount': bounce_amount,
                        'touch_count': touch_count,
                        'candle_index': len(ohlcv) - len(recent_candles) + i
                    })
                # State transition: above → below
                elif not curr_above and prev_above is True:
                    touch_count = 0  # Reset counter
                    events.append({
                        'date': date,
                        'state': 'below',
                        'close': close,
                        'volume': volume,
                        'event': 'failed',
                        'touch_count': touch_count,
                        'candle_index': len(ohlcv) - len(recent_candles) + i
                    })
                # First event
                elif prev_above is None:
                    if curr_above:
                        events.append({
                            'date': date,
                            'state': 'above',
                            'close': close,
                            'volume': volume,
                            'event': 'breakout',
                            'candle_index': len(ohlcv) - len(recent_candles) + i
                        })
                    else:
                        events.append({
                            'date': date,
                            'state': 'below',
                            'close': close,
                            'volume': volume,
                            'event': 'below',
                            'candle_index': len(ohlcv) - len(recent_candles) + i
                        })
            
            # Current state
            if events:
                current_state = events[-1]['state']
        
        elif element_type == 'diagonal_line':
            # Get trend line type to determine correct event naming
            trend_line_type = element.get('trend_line_type', '')
            
            # Analyze recent candles with proper state transitions
            for i, candle in enumerate(recent_candles):
                timestamp, open_price, high, low, close, volume = candle
                date = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d')
                
                # Calculate diagonal price at this time
                diagonal_price = self.calculate_diagonal_price_at_time(element, timestamp)
                if diagonal_price == 0:
                    continue
                
                # Determine current state
                curr_above = close > diagonal_price
                prev_above = events[-1]['state'] == 'above' if events else None
                
                # State transition: below → above
                if curr_above and prev_above is False:
                    # Use correct event naming based on trend line type
                    if trend_line_type == 'resistance':
                        event_name = 'breakout'
                    elif trend_line_type == 'support':
                        event_name = 'reclaim'
                    else:
                        event_name = 'breakout'  # Default fallback
                    
                    events.append({
                        'date': date,
                        'state': 'above',
                        'close': close,
                        'diagonal_price': diagonal_price,
                        'volume': volume,
                        'event': event_name,
                        'candle_index': len(ohlcv) - len(recent_candles) + i
                    })
                # State transition: above → below
                elif not curr_above and prev_above is True:
                    # Use correct event naming based on trend line type
                    if trend_line_type == 'resistance':
                        event_name = 'breakbelow'
                    elif trend_line_type == 'support':
                        event_name = 'failed'
                    else:
                        event_name = 'breakbelow'  # Default fallback
                    
                    events.append({
                        'date': date,
                        'state': 'below',
                        'close': close,
                        'diagonal_price': diagonal_price,
                        'volume': volume,
                        'event': event_name,
                        'candle_index': len(ohlcv) - len(recent_candles) + i
                    })
                # First event
                elif prev_above is None:
                    if curr_above:
                        # Use correct event naming based on trend line type
                        if trend_line_type == 'resistance':
                            event_name = 'breakout'
                        elif trend_line_type == 'support':
                            event_name = 'reclaim'
                        else:
                            event_name = 'breakout'  # Default fallback
                        
                        events.append({
                            'date': date,
                            'state': 'above',
                            'close': close,
                            'diagonal_price': diagonal_price,
                            'volume': volume,
                            'event': event_name,
                            'candle_index': len(ohlcv) - len(recent_candles) + i
                        })
                    else:
                        # Use correct event naming based on trend line type
                        if trend_line_type == 'resistance':
                            event_name = 'breakbelow'
                        elif trend_line_type == 'support':
                            event_name = 'failed'
                        else:
                            event_name = 'breakbelow'  # Default fallback
                        
                        events.append({
                            'date': date,
                            'state': 'below',
                            'close': close,
                            'diagonal_price': diagonal_price,
                            'volume': volume,
                            'event': event_name,
                            'candle_index': len(ohlcv) - len(recent_candles) + i
                        })
            
            # Current state
            if events:
                current_state = events[-1]['state']
        
        elif element_type == 'zone':
            zone_top = element.get('price_top', 0.0)
            zone_bottom = element.get('price_bottom', 0.0)
            
            if zone_top == 0 or zone_bottom == 0:
                return {"error": "No price data for zone"}
            
            # Analyze recent candles with proper state transitions
            for i, candle in enumerate(recent_candles):
                timestamp, open_price, high, low, close, volume = candle
                date = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d')
                
                # Determine current state
                if close > zone_top:
                    curr_state = 'above'
                elif close < zone_bottom:
                    curr_state = 'below'
                else:
                    curr_state = 'inside'
                
                prev_state = events[-1]['state'] if events else None
                
                # State transitions
                if curr_state != prev_state:
                    if curr_state == 'above' and prev_state in ['below', 'inside']:
                        event = f'{element_id}_top_reclaim'
                    elif curr_state == 'below' and prev_state in ['above', 'inside']:
                        event = f'{element_id}_bottom_failed'
                    elif curr_state == 'inside' and prev_state == 'above':
                        event = f'{element_id}_top_failed'
                    elif curr_state == 'inside' and prev_state == 'below':
                        event = f'{element_id}_bottom_reclaim'
                    else:
                        event = 'inside_zone'
                    
                    events.append({
                        'date': date,
                        'state': curr_state,
                        'close': close,
                        'zone_top': zone_top,
                        'zone_bottom': zone_bottom,
                        'volume': volume,
                        'event': event,
                        'candle_index': len(ohlcv) - len(recent_candles) + i
                    })
            
            # Current state
            if events:
                current_state = events[-1]['state']
        
        return {
            'element_id': element_id,
            'element_type': element_type,
            'current_state': current_state,
            'events': events,
            'total_events': len(events)
        }
    
    def analyze_volume_story(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze volume patterns for the events"""
        if not events:
            return {"volume_story": "no_events"}
        
        # Get volumes for each event
        volumes = [event.get('volume', 0) for event in events if event.get('volume')]
        
        if not volumes:
            return {"volume_story": "no_volume_data"}
        
        # Calculate volume metrics
        avg_volume = sum(volumes) / len(volumes)
        max_volume = max(volumes)
        min_volume = min(volumes)
        
        # Find high volume events
        high_volume_events = [e for e in events if e.get('volume', 0) > avg_volume * 1.5]
        
        # Volume trend
        if len(volumes) >= 3:
            recent_avg = sum(volumes[-3:]) / 3
            earlier_avg = sum(volumes[-6:-3]) / 3 if len(volumes) >= 6 else recent_avg
            volume_trend = "increasing" if recent_avg > earlier_avg else "decreasing"
        else:
            volume_trend = "insufficient_data"
        
        return {
            "volume_story": {
                "avg_volume": round(avg_volume, 0),
                "max_volume": max_volume,
                "min_volume": min_volume,
                "high_volume_events": len(high_volume_events),
                "volume_trend": volume_trend,
                "recent_volume": volumes[-1] if volumes else 0
            }
        }
    
    def filter_events_three_sections(self, events: List[Dict[str, Any]], ohlcv: List[List]) -> Dict[str, Any]:
        """Filter events using 3-section approach"""
        total_candles = len(ohlcv)
        
        # Section A: Full range (all time) - max 3 events
        section_a_events = self._get_top_volume_events(events, 3)
        
        # Section B: Last 2/3 of candles - max 3 events
        section_b_start = total_candles // 3
        section_b_events = self._get_top_volume_events(
            [e for e in events if e.get('candle_index', 0) >= section_b_start], 3
        )
        
        # Section C: Last 1/6 of candles - per element analysis
        section_c_start = total_candles * 5 // 6
        section_c_events = self._analyze_recent_activity(
            [e for e in events if e.get('candle_index', 0) >= section_c_start]
        )
        
        return {
            'global_significant': section_a_events,
            'recent_significant': section_b_events,
            'current_activity': section_c_events
        }
    
    def _get_top_volume_events(self, events: List[Dict[str, Any]], max_events: int) -> List[Dict[str, Any]]:
        """Get top events by volume"""
        if not events:
            return []
        
        # Sort by volume (descending)
        sorted_events = sorted(events, key=lambda x: x.get('volume', 0), reverse=True)
        return sorted_events[:max_events]
    
    def _analyze_recent_activity(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze recent activity per element"""
        if not events:
            return {}
        
        # Group events by element
        element_events = {}
        for event in events:
            element_id = event.get('element_id', 'unknown')
            if element_id not in element_events:
                element_events[element_id] = []
            element_events[element_id].append(event)
        
        # Analyze each element's recent activity
        recent_analysis = {}
        for element_id, element_event_list in element_events.items():
            # Calculate volume threshold for this element
            volumes = [e.get('volume', 0) for e in element_event_list if e.get('volume')]
            if not volumes:
                continue
                
            avg_volume = sum(volumes) / len(volumes)
            volume_threshold = avg_volume * 0.8
            
            # Filter events above threshold
            important_events = [e for e in element_event_list if e.get('volume', 0) >= volume_threshold]
            
            # Limit to 10 events max
            if len(important_events) > 10:
                important_events = important_events[:10]
            
            recent_analysis[element_id] = {
                'events': important_events,
                'total_events': len(element_event_list),
                'important_events': len(important_events),
                'volume_threshold': volume_threshold
            }
        
        return recent_analysis
    
    def _calculate_element_sequences(self) -> Dict[str, Dict[str, Any]]:
        """Calculate event sequences for all elements with enhanced structure for Stage 6B"""
        element_sequences = {}
        ohlcv = self.ohlc_data.get('ohlcv', [])
        
        if not ohlcv:
            self.missing_data.append("ohlc_data.ohlcv for element sequences")
            return {}
        
        # Collect all events from all elements for 3-section analysis
        all_events = []
        element_data = {}
        
        for element_id, element in self.elements.items():
            try:
                sequence_data = self.analyze_element_sequence(element_id, element, ohlcv)
                element_data[element_id] = sequence_data
                
                # Add element_id to each event for filtering
                for event in sequence_data.get('events', []):
                    event['element_id'] = element_id
                    all_events.append(event)
                    
            except Exception as e:
                logger.warning(f"Error analyzing element {element_id}: {e}")
                element_data[element_id] = {
                    "error": str(e),
                    "element_type": element.get('element_type', 'unknown'),
                    "current_state": "unknown",
                    "events": [],
                    "total_events": 0
                }
        
        # Apply 3-section filtering
        three_sections = self.filter_events_three_sections(all_events, ohlcv)
        
        # Build final element sequences with enhanced structure for Stage 6B
        for element_id, sequence_data in element_data.items():
            if 'error' in sequence_data:
                element_sequences[element_id] = {
                    "type": sequence_data.get('element_type', 'unknown'),
                    "current_state": "unknown",
                    "total_events": 0,
                    "recent_events": [],
                    "volume_story": "error",
                    "error": sequence_data.get('error', 'unknown')
                }
                continue
            
            # Get events for this element
            element_events = [e for e in sequence_data.get('events', [])]
            
            # Calculate enhanced data for Stage 6B
            element = self.elements[element_id]
            element_type = element.get('element_type', 'unknown')
            
            # Current diagonal price and distance for diagonal lines
            current_diagonal_price = 0.0
            pct_to_trigger = 0.0
            window = {}
            
            if element_type == 'diagonal_line':
                current_diagonal_price = self._get_current_diagonal_price(element)
                if current_diagonal_price > 0:
                    pct_to_trigger = abs((self.current_price - current_diagonal_price) / current_diagonal_price) * 100
                
                # Time window for diagonal
                price_time_points = element.get('price_time_points', [])
                if price_time_points:
                    window = {
                        "start": datetime.fromtimestamp(price_time_points[0][0], tz=timezone.utc).isoformat(),
                        "end": datetime.fromtimestamp(price_time_points[-1][0], tz=timezone.utc).isoformat()
                    }
            
            # Per-element volume baseline
            element_volumes = [e.get('volume', 0) for e in element_events if e.get('volume', 0) > 0]
            element_avg_vol = sum(element_volumes) / len(element_volumes) if element_volumes else 0
            vol_gate_1p5x = element_avg_vol * 1.5
            
            # Retest detection
            retest_detection = self._detect_retest(element_events, element_type)
            
            # Distances to levels
            distances = self._calculate_distances_to_levels(element, element_type)
            
            # Normalized events with structured data
            structured_events = []
            ohlcv = self.ohlc_data.get('ohlcv', [])
            for event in element_events[-5:]:  # Last 5 events
                candle_index = event.get('candle_index', 0)
                ts_ms = ohlcv[candle_index][0] if 0 <= candle_index < len(ohlcv) else None
                structured_events.append({
                    "event_kind": event.get('event', 'unknown'),
                    "side": self._determine_event_side(event.get('event', '')),
                    "price_at_event": event.get('close', 0),
                    "volume": event.get('volume', 0),
                    "candle_index": candle_index,
                    "ts_ms": ts_ms,
                    "date": datetime.fromtimestamp(ts_ms/1000, tz=timezone.utc).isoformat() if ts_ms else event.get('date', 'unknown')
                })
            
            # Calculate meaningful volume story with price context
            volume_story = self._calculate_meaningful_volume_story(element_events)
            
            # Determine current state based on recent activity
            current_state = self._determine_current_state(element_events, sequence_data.get('current_state', 'unknown'))
            
            # Get global/recent event references for this element
            global_events = [e for e in three_sections.get('global_significant', []) if e.get('element_id') == element_id]
            recent_events_refs = [e for e in three_sections.get('recent_significant', []) if e.get('element_id') == element_id]
            
            element_sequences[element_id] = {
                # Basic info
                "type": sequence_data.get('element_type', 'unknown'),
                "trend_line_type": element.get('trend_line_type', ''),
                "current_state": current_state,
                "total_events": sequence_data.get('total_events', 0),
                
                # Enhanced data for Stage 6B
                "now_price_at_element": current_diagonal_price if element_type == 'diagonal_line' else element.get('price', 0),
                "pct_to_trigger": pct_to_trigger,
                "window": window,
                "volume_baseline": {
                    "avg_events": element_avg_vol,
                    "vol_gate_1p5x": vol_gate_1p5x
                },
                "retest_detection": retest_detection,
                "distances": distances,
                "structured_events": structured_events,
                
                # Legacy fields for compatibility
                "recent_events": [f"{e['date']}: {e['event_kind']} (close: {e['price_at_event']:.4f}, vol: {e['volume']:,.0f})" for e in structured_events],
                "volume_story": volume_story,
                "global_events": global_events,
                "recent_events_refs": recent_events_refs,
                "current_activity": three_sections.get('current_activity', {}).get(element_id, {}),
                
                # Key level data
                "price": element.get('price', 0),
                "price_top": element.get('price_top', 0),
                "price_bottom": element.get('price_bottom', 0)
            }
        
        return element_sequences, all_events
    
    def _detect_retest(self, element_events: List[Dict[str, Any]], element_type: str) -> Dict[str, Any]:
        """Detect retest patterns for an element"""
        if not element_events:
            return {"seen": False, "within_n": 0, "band_pct": 0.0, "last_retest_idx": None}
        
        # Look for breakout followed by retest within 10 candles
        breakout_events = []
        retest_events = []
        
        for i, event in enumerate(element_events):
            event_kind = event.get('event', '')
            if 'breakout' in event_kind.lower() or 'reclaim' in event_kind.lower():
                breakout_events.append((i, event))
            elif 'retest' in event_kind.lower() or 'failed' in event_kind.lower():
                retest_events.append((i, event))
        
        if not breakout_events:
            return {"seen": False, "within_n": 0, "band_pct": 0.0, "last_retest_idx": None}
        
        # Check for retest within 10 candles of last breakout
        last_breakout_idx = breakout_events[-1][0]
        recent_retests = [r for r in retest_events if r[0] > last_breakout_idx and r[0] - last_breakout_idx <= 10]
        
        if recent_retests:
            last_retest_idx, last_retest = recent_retests[-1]
            return {
                "seen": True,
                "within_n": last_retest_idx - last_breakout_idx,
                "band_pct": 0.8,  # Default retest band
                "last_retest_list_idx": last_retest_idx,
                "last_retest_candle_index": last_retest.get('candle_index', 0)
            }
        
        return {"seen": False, "within_n": 0, "band_pct": 0.0, "last_retest_idx": None}
    
    def _calculate_distances_to_levels(self, element: Dict[str, Any], element_type: str) -> Dict[str, float]:
        """Calculate distances to key levels for an element"""
        current_price = self.current_price
        distances = {}
        
        if element_type == 'horizontal_line':
            price = element.get('price', 0)
            if price > 0:
                distances["to_level"] = abs(current_price - price)
                distances["to_level_pct"] = abs((current_price - price) / price) * 100
        
        elif element_type == 'zone':
            price_top = element.get('price_top', 0)
            price_bottom = element.get('price_bottom', 0)
            if price_top > 0 and price_bottom > 0:
                distances["to_top"] = abs(current_price - price_top)
                distances["to_bottom"] = abs(current_price - price_bottom)
                distances["to_top_pct"] = abs((current_price - price_top) / price_top) * 100
                distances["to_bottom_pct"] = abs((current_price - price_bottom) / price_bottom) * 100
        
        elif element_type == 'diagonal_line':
            current_diagonal_price = self._get_current_diagonal_price(element)
            if current_diagonal_price > 0:
                distances["to_line"] = abs(current_price - current_diagonal_price)
                distances["to_line_pct"] = abs((current_price - current_diagonal_price) / current_diagonal_price) * 100
        
        return distances
    
    def _determine_event_side(self, event_kind: str) -> str:
        """Determine if an event is bullish or bearish"""
        bullish_events = ['breakout', 'reclaim', 'bounce']
        bearish_events = ['breakdown', 'failed', 'breakbelow']
        
        event_lower = event_kind.lower()
        if any(bull in event_lower for bull in bullish_events):
            return 'bull'
        elif any(bear in event_lower for bear in bearish_events):
            return 'bear'
        else:
            return 'neutral'
    
    def _calculate_meaningful_volume_story(self, events: List[Dict[str, Any]]) -> str:
        """Calculate volume story with price context"""
        if not events:
            return "no_events"
        
        # Get recent events (last 5)
        recent_events = events[-5:] if len(events) >= 5 else events
        
        if len(recent_events) < 2:
            return "insufficient_data"
        
        # Calculate volume metrics
        volumes = [e.get('volume', 0) for e in recent_events if e.get('volume')]
        if not volumes:
            return "no_volume_data"
        
        avg_volume = sum(volumes) / len(volumes)
        recent_volume = volumes[-1]
        
        # Analyze price direction vs volume
        price_changes = []
        for i in range(1, len(recent_events)):
            prev_close = recent_events[i-1].get('close', 0)
            curr_close = recent_events[i].get('close', 0)
            if prev_close > 0:
                price_change = (curr_close - prev_close) / prev_close
                price_changes.append(price_change)
        
        if not price_changes:
            return f"avg_vol={avg_volume:,.0f}, recent_vol={recent_volume:,.0f}"
        
        avg_price_change = sum(price_changes) / len(price_changes)
        
        # Determine volume-price relationship
        if recent_volume > avg_volume * 1.5:  # High volume
            if avg_price_change > 0.02:  # Price up
                volume_context = "high_vol_bullish"
            elif avg_price_change < -0.02:  # Price down
                volume_context = "high_vol_bearish"
            else:
                volume_context = "high_vol_neutral"
        elif recent_volume < avg_volume * 0.5:  # Low volume
            if avg_price_change > 0.02:
                volume_context = "low_vol_weak_bullish"
            elif avg_price_change < -0.02:
                volume_context = "low_vol_weak_bearish"
            else:
                volume_context = "low_vol_neutral"
        else:  # Normal volume
            if avg_price_change > 0.02:
                volume_context = "normal_vol_bullish"
            elif avg_price_change < -0.02:
                volume_context = "normal_vol_bearish"
            else:
                volume_context = "normal_vol_neutral"
        
        return f"{volume_context} (avg={avg_volume:,.0f}, recent={recent_volume:,.0f}, price_chg={avg_price_change:+.1%})"
    
    def _determine_current_state(self, events: List[Dict[str, Any]], fallback_state: str) -> str:
        """Determine current state based on recent activity"""
        if not events:
            return fallback_state
        
        # Look at last 3 events to determine current state
        recent_events = events[-3:] if len(events) >= 3 else events
        
        # Define bullish and bearish event patterns
        bullish_events = {'breakout', 'reclaim', 'bounce'}
        bearish_events = {'breakdown', 'failed', 'breakbelow'}
        
        def is_bullish(event):
            event_name = event.get('event', '').lower()
            return any(pattern in event_name for pattern in bullish_events)
        
        def is_bearish(event):
            event_name = event.get('event', '').lower()
            return any(pattern in event_name for pattern in bearish_events)
        
        # Check for recent breakouts/breakdowns
        recent_breakouts = [e for e in recent_events if is_bullish(e)]
        recent_breakdowns = [e for e in recent_events if is_bearish(e)]
        
        if recent_breakouts and not recent_breakdowns:
            return "recent_breakout"
        elif recent_breakdowns and not recent_breakouts:
            return "recent_breakdown"
        elif recent_breakouts and recent_breakdowns:
            return "mixed_recent_activity"
        else:
            # No recent breakouts/breakdowns, use position-based state
            return fallback_state
    
    def _calculate_volume_analysis(self, element_sequences: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate contextual volume analysis from OHLC data and element events"""
        ohlcv = self.ohlc_data.get('ohlcv', [])
        
        if not ohlcv:
            self.missing_data.append("ohlc_data.ohlcv for volume analysis")
            return {
                "current_volume": None,
                "recent_average": None,
                "volume_trend": "unknown",
                "breakout_volume_analysis": {"overall": "unknown"}
            }
        
        # Extract volumes (index 5 in OHLCV)
        volumes = [candle[5] for candle in ohlcv]
        
        # Current day volume
        current_volume = volumes[-1] if volumes else None
        
        # Recent average (last 7 days)
        recent_volumes = volumes[-7:] if len(volumes) >= 7 else volumes
        recent_average = statistics.mean(recent_volumes) if recent_volumes else None
        
        # Volume trend (comparing last 3 vs previous 3)
        if len(volumes) >= 6:
            last_3_avg = statistics.mean(volumes[-3:])
            prev_3_avg = statistics.mean(volumes[-6:-3])
            volume_trend = "increasing" if last_3_avg > prev_3_avg else "decreasing"
        else:
            volume_trend = "insufficient_data"
        
        # Analyze breakout volumes from element events
        breakout_events = []
        for element_id, element_data in element_sequences.items():
            if 'error' in element_data:
                continue
                
            recent_events = element_data.get('recent_events', [])
            for event_str in recent_events[-5:]:  # Last 5 events
                # Only include actual breakouts (not reclaims or failed)
                if 'breakout' in event_str.lower() and 'reclaim' not in event_str.lower() and 'failed' not in event_str.lower():
                    # Extract volume from event string
                    if 'vol:' in event_str:
                        try:
                            vol_part = event_str.split('vol:')[1].split(')')[0].replace(',', '')
                            volume = float(vol_part)
                            date_part = event_str.split(':')[0]
                            event_type = event_str.split(':')[1].split('(')[0].strip()
                            
                            breakout_events.append({
                                "date": date_part,
                                "event": event_type,
                                "volume": volume,
                                "element_id": element_id
                            })
                        except:
                            pass
        
        # Analyze breakout volume strength
        if breakout_events:
            breakout_volumes = [e['volume'] for e in breakout_events]
            avg_breakout_volume = statistics.mean(breakout_volumes)
            max_breakout_volume = max(breakout_volumes)
            
            # Compare to recent average
            if recent_average:
                if avg_breakout_volume > recent_average * 1.5:
                    overall_breakout_strength = "strong"
                elif avg_breakout_volume > recent_average:
                    overall_breakout_strength = "moderate"
                else:
                    overall_breakout_strength = "weak"
            else:
                overall_breakout_strength = "unknown"
        else:
            overall_breakout_strength = "no_breakouts"
            avg_breakout_volume = 0
            max_breakout_volume = 0
        
        return {
            "current_volume": current_volume,
            "recent_average": recent_average,
            "volume_trend": volume_trend,
            "breakout_volume_analysis": {
                "overall": overall_breakout_strength,
                "average_breakout_volume": avg_breakout_volume,
                "max_breakout_volume": max_breakout_volume,
                "recent_breakouts": breakout_events[-3:] if breakout_events else [],  # Last 3 breakouts
                "breakout_count": len(breakout_events)
            }
        }
    
    
    
    def _calculate_volatility(self) -> Dict[str, Any]:
        """Calculate volatility analysis from OHLC data"""
        ohlcv = self.ohlc_data.get('ohlcv', [])
        
        if len(ohlcv) < 2:
            return {
                "current_volatility": 0.0,
                "historical_volatility": 0.0,
                "volatility_ratio": 0.0,
                "volatility_label": "unknown"
            }
        
        # Calculate daily returns
        closes = [candle[4] for candle in ohlcv[-20:]]  # Last 20 days
        returns = []
        
        for i in range(1, len(closes)):
            daily_return = (closes[i] - closes[i-1]) / closes[i-1]
            returns.append(daily_return)
        
        if not returns:
            return {
                "current_volatility": 0.0,
                "historical_volatility": 0.0,
                "volatility_ratio": 0.0,
                "volatility_label": "unknown"
            }
        
        # Current volatility (last 20 days)
        current_vol = statistics.stdev(returns) * (252 ** 0.5)  # Annualized
        
        # Historical volatility (last 60 days if available)
        if len(ohlcv) >= 60:
            historical_closes = [candle[4] for candle in ohlcv[-60:]]
            historical_returns = []
            for i in range(1, len(historical_closes)):
                daily_return = (historical_closes[i] - historical_closes[i-1]) / historical_closes[i-1]
                historical_returns.append(daily_return)
            historical_vol = statistics.stdev(historical_returns) * (252 ** 0.5)
        else:
            historical_vol = current_vol
        
        # Calculate ratio
        volatility_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
        
        # Label volatility
        if current_vol > 0.8:
            volatility_label = "very_high"
        elif current_vol > 0.5:
            volatility_label = "high"
        elif current_vol > 0.2:
            volatility_label = "normal"
        else:
            volatility_label = "low"
        
        return {
            "current_volatility": round(current_vol, 4),
            "historical_volatility": round(historical_vol, 4),
            "volatility_ratio": round(volatility_ratio, 2),
            "volatility_label": volatility_label
        }
    
    def _get_pattern_formation_dates(self) -> Tuple[Optional[str], Optional[str]]:
        """Get pattern formation start and end dates"""
        # For now, use OHLC date range as placeholder
        # This should be enhanced to analyze actual pattern formation
        ohlcv = self.ohlc_data.get('ohlcv', [])
        
        if not ohlcv:
            return None, None
        
        # Use first and last candle dates as rough approximation
        start_timestamp = ohlcv[0][0] / 1000  # Convert from milliseconds
        end_timestamp = ohlcv[-1][0] / 1000
        
        start_date = datetime.fromtimestamp(start_timestamp, tz=timezone.utc).isoformat()
        end_date = datetime.fromtimestamp(end_timestamp, tz=timezone.utc).isoformat()
        
        return start_date, end_date
    
    def _get_global_and_recent_events(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get global and recent significant events separately"""
        ohlcv = self.ohlc_data.get('ohlcv', [])
        if not ohlcv:
            return [], []
        
        # Collect all events from all elements
        all_events = []
        for element_id, element in self.elements.items():
            try:
                sequence_data = self.analyze_element_sequence(element_id, element, ohlcv)
                for event in sequence_data.get('events', []):
                    event['element_id'] = element_id
                    all_events.append(event)
            except Exception as e:
                logger.warning(f"Error analyzing element {element_id}: {e}")
                continue
        
        # Apply 3-section filtering
        three_sections = self.filter_events_three_sections(all_events, ohlcv)
        
        # Return global and recent events
        global_events = three_sections.get('global_significant', [])
        recent_events = three_sections.get('recent_significant', [])
        
        return global_events, recent_events
    
    def _get_global_and_recent_events_from_all(self, all_events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get global and recent significant events from pre-computed all_events"""
        ohlcv = self.ohlc_data.get('ohlcv', [])
        if not ohlcv:
            return [], []
        
        # Apply 3-section filtering
        three_sections = self.filter_events_three_sections(all_events, ohlcv)
        
        return three_sections.get('global_significant', []), three_sections.get('recent_significant', [])
    
    def _calculate_overview_analysis(self, element_sequences: Dict[str, Dict[str, Any]], global_events: List[Dict[str, Any]], recent_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overview analysis from element-level data"""
        
        # Analyze breakout status from element states
        breakout_states = []
        volume_confirmations = []
        key_levels = {"resistance": [], "support": [], "zones": []}
        
        for element_id, element_data in element_sequences.items():
            if 'error' in element_data:
                continue
                
            current_state = element_data.get('current_state', 'unknown')
            element_type = element_data.get('type', 'unknown')
            trend_line_type = element_data.get('trend_line_type', '')
            
            # Collect breakout states
            if current_state in ['recent_breakout', 'recent_breakdown', 'mixed_recent_activity']:
                breakout_states.append(current_state)
            
            # Analyze volume confirmation from recent events using per-element baselines
            recent_events_list = element_data.get('recent_events', [])
            if recent_events_list:
                # Get per-element volume baseline
                gate = element_data.get("volume_baseline", {}).get("vol_gate_1p5x")
                if gate is not None:
                    # Check if recent breakouts had high volume
                    for event_str in recent_events_list[-3:]:  # Last 3 events
                        if 'breakout' in event_str or 'reclaim' in event_str:
                            # Extract volume from event string
                            if 'vol:' in event_str:
                                try:
                                    vol_part = event_str.split('vol:')[1].split(')')[0].replace(',', '')
                                    volume = float(vol_part)
                                    # Use per-element volume gate
                                    if volume > gate:
                                        volume_confirmations.append(True)
                                    else:
                                        volume_confirmations.append(False)
                                except:
                                    pass
            
            # Collect key levels
            if element_type == 'horizontal_line':
                price = element_data.get('price', 0)
                if price > 0:
                    if current_state == 'below':
                        key_levels["resistance"].append(price)
                    else:
                        key_levels["support"].append(price)
            elif element_type == 'diagonal_line':
                # For diagonal lines, calculate current diagonal price
                element = self.elements[element_id]
                current_diagonal_price = self._get_current_diagonal_price(element)
                if current_diagonal_price > 0:
                    if trend_line_type == 'resistance':
                        key_levels["resistance"].append(current_diagonal_price)
                    elif trend_line_type == 'support':
                        key_levels["support"].append(current_diagonal_price)
            elif element_type == 'zone':
                # Get zone data directly from elements
                element = self.elements.get(element_id, {})
                price_top = element.get('price_top', 0)
                price_bottom = element.get('price_bottom', 0)
                if price_top > 0 and price_bottom > 0:
                    key_levels["zones"].append({
                        "id": element_id,
                        "top": price_top, 
                        "bottom": price_bottom
                    })
        
        # Determine overall breakout status
        if not breakout_states:
            breakout_status = "none"
        elif all(state == 'recent_breakout' for state in breakout_states):
            breakout_status = "broken_out"
        elif all(state == 'recent_breakdown' for state in breakout_states):
            breakout_status = "broken_down"
        else:
            breakout_status = "mixed"
        
        # Determine volume confirmation
        volume_confirmation = len(volume_confirmations) > 0 and sum(volume_confirmations) > len(volume_confirmations) / 2
        
        # Determine momentum direction
        recent_breakout_count = sum(1 for state in breakout_states if 'breakout' in state)
        recent_breakdown_count = sum(1 for state in breakout_states if 'breakdown' in state)
        
        if recent_breakout_count > recent_breakdown_count:
            momentum_direction = "up"
        elif recent_breakdown_count > recent_breakout_count:
            momentum_direction = "down"
        else:
            momentum_direction = "sideways"
        
        # Determine current position relative to key levels
        current_price = self.current_price
        position_analysis = self._analyze_current_position(current_price, key_levels)
        
        return {
            "breakout_status": breakout_status,
            "breakout_confirmation": breakout_status in ["broken_out", "mixed"],
            "volume_confirmation": volume_confirmation,
            "momentum_direction": momentum_direction,
            "key_levels": {
                "resistance": sorted(key_levels["resistance"], reverse=True)[:3],  # Top 3
                "support": sorted(key_levels["support"])[:3],  # Bottom 3
                "zones": key_levels["zones"][:3]  # Top 3 zones
            },
            "current_position": position_analysis,
            "recent_activity_summary": {
                "breakout_states": breakout_states,
                "volume_confirmations": volume_confirmations,
                "active_elements": len([e for e in element_sequences.values() if e.get('current_state') not in ['unknown', 'below']])
            }
        }
    
    def _get_current_diagonal_price(self, element: Dict[str, Any]) -> float:
        """Get current diagonal price for an element with caching"""
        if element.get('element_type') != 'diagonal_line':
            return 0.0
            
        # Use element ID for caching
        element_id = element.get('id') or id(element)
        if element_id in self._diag_now_cache:
            return self._diag_now_cache[element_id]
            
        # Get current timestamp
        ohlcv = self.ohlc_data.get('ohlcv', [])
        if not ohlcv:
            return 0.0
            
        current_timestamp = ohlcv[-1][0]  # Latest candle timestamp
        price = self.calculate_diagonal_price_at_time(element, current_timestamp)
        self._diag_now_cache[element_id] = price
        return price
    
    def _analyze_current_position(self, current_price: float, key_levels: Dict[str, List[float]]) -> str:
        """Analyze current price position relative to key levels"""
        # Check if price is in a zone first
        for zone in key_levels["zones"]:
            if zone["bottom"] <= current_price <= zone["top"]:
                return "inside_zone"
        
        # Check if price is above resistance
        if key_levels["resistance"]:
            max_resistance = max(key_levels["resistance"])
            if current_price > max_resistance:
                return "above_resistance"
        
        # Check if price is below support
        if key_levels["support"]:
            min_support = min(key_levels["support"])
            if current_price < min_support:
                return "below_support"
        
        # If we have any levels, determine position
        if key_levels["resistance"] or key_levels["support"] or key_levels["zones"]:
            return "between_levels"
        
        return "no_key_levels"
    
    def _calculate_execution_readiness(self, overview_analysis: Dict[str, Any]) -> str:
        """Calculate execution readiness based on breakout status and volume confirmation"""
        breakout_status = overview_analysis.get('breakout_status', 'none')
        volume_confirmation = overview_analysis.get('volume_confirmation', False)
        current_position = overview_analysis.get('current_position', 'unknown')
        
        # If no breakout, not ready
        if breakout_status == 'none':
            return "not_ready"
        
        # If broken out but no volume confirmation, wait for volume
        if breakout_status == 'broken_out' and not volume_confirmation:
            return "wait_volume"
        
        # If broken out with volume confirmation, ready
        if breakout_status == 'broken_out' and volume_confirmation:
            return "ready"
        
        # If inside zone, might be ready for range trading
        if current_position == 'inside_zone':
            return "ready"
        
        # If between levels, wait for retest
        if current_position == 'between_levels':
            return "wait_retest"
        
        return "not_ready"
    
    def _calculate_derived_levels(self, overview_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived support/resistance levels based on current position"""
        current_position = overview_analysis.get('current_position', '')
        key_levels = overview_analysis.get('key_levels', {})
        zones = key_levels.get('zones', [])
        
        # If inside a zone, use that zone's levels as primary
        if current_position == 'inside_zone' and zones:
            # Find the zone that contains the current price
            current_price = self.current_price
            current_zone = None
            for zone in zones:
                if zone.get('bottom', 0) <= current_price <= zone.get('top', 0):
                    current_zone = zone
                    break
            
            if current_zone:
                # Find secondary resistance (next zone up)
                other_zones = [z for z in zones if z.get('id') != current_zone.get('id')]
                secondary_resistance = None
                if other_zones:
                    # Find the next zone above current zone
                    zones_above = [z for z in other_zones if z.get('bottom', 0) > current_zone.get('top', 0)]
                    if zones_above:
                        secondary_resistance = min(z.get('bottom', 0) for z in zones_above)
                    else:
                        secondary_resistance = max(z.get('top', 0) for z in other_zones)
                
                return {
                    "support_primary": current_zone.get('bottom'),
                    "resistance_primary": current_zone.get('top'),
                    "resistance_secondary": secondary_resistance
                }
        
        # Fallback to general zone levels
        if zones:
            return {
                "support_primary": min(z.get('bottom', 0) for z in zones),
                "resistance_primary": max(z.get('top', 0) for z in zones),
                "resistance_secondary": None
            }
        
        return {
            "support_primary": None,
            "resistance_primary": None,
            "resistance_secondary": None
        }
    
    def _calculate_state_machine_mode(self, overview_analysis: Dict[str, Any], volume_analysis: Dict[str, Any]) -> Dict[str, str]:
        """Calculate state machine mode and reason"""
        current_position = overview_analysis.get('current_position', '')
        volume_trend = volume_analysis.get('volume_trend', 'unknown')
        breakout_status = overview_analysis.get('breakout_status', 'none')
        
        # If inside zone with volume down and breakouts fading
        if current_position == 'inside_zone':
            if volume_trend == 'decreasing' and breakout_status == 'broken_out':
                return {
                    "mode": "range",
                    "reason": "inside_support_zone + volume_down_breakouts_fade"
                }
            else:
                return {
                    "mode": "range",
                    "reason": "inside_zone_consolidation"
                }
        
        # If above resistance with volume confirmation
        elif current_position == 'above_resistance':
            if volume_trend == 'increasing':
                return {
                    "mode": "trend",
                    "reason": "above_resistance + volume_confirmed"
                }
            else:
                return {
                    "mode": "neutral",
                    "reason": "above_resistance + low_volume"
                }
        
        # If below support
        elif current_position == 'below_support':
            return {
                "mode": "breakdown",
                "reason": "below_support_level"
            }
        
        # Default neutral
        return {
            "mode": "neutral",
            "reason": "between_levels"
        }
    
    def _calculate_side(self, overview_analysis: Dict[str, Any]) -> str:
        """Calculate trading side based on position and breakout status"""
        current_position = overview_analysis.get('current_position', '')
        breakout_status = overview_analysis.get('breakout_status', 'none')
        
        # If inside zone, prefer long (buy the dip)
        if current_position == 'inside_zone':
            return "long"
        
        # If broken out above resistance, long
        if current_position == 'above_resistance' and breakout_status == 'broken_out':
            return "long"
        
        # If below support, short
        if current_position == 'below_support':
            return "short"
        
        # Default to long for range trading
        return "long"
    
    def _calculate_invalidation_levels(self, overview_analysis: Dict[str, Any]) -> List[float]:
        """Calculate invalidation levels"""
        current_position = overview_analysis.get('current_position', '')
        key_levels = overview_analysis.get('key_levels', {})
        zones = key_levels.get('zones', [])
        
        # If inside a zone, use zone bottom as invalidation
        if current_position == 'inside_zone' and zones:
            current_price = self.current_price
            for zone in zones:
                if zone.get('bottom', 0) <= current_price <= zone.get('top', 0):
                    return [zone.get('bottom', 0)]
        
        # Fallback to support levels
        support_levels = key_levels.get('support', [])
        if support_levels:
            return [min(support_levels)]
        
        return []
    
    def _calculate_rr_estimate(self, overview_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk-reward estimate"""
        current_position = overview_analysis.get('current_position', '')
        key_levels = overview_analysis.get('key_levels', {})
        zones = key_levels.get('zones', [])
        
        if current_position == 'inside_zone' and zones:
            current_price = self.current_price
            for zone in zones:
                if zone.get('bottom', 0) <= current_price <= zone.get('top', 0):
                    zone_bottom = zone.get('bottom', 0)
                    zone_top = zone.get('top', 0)
                    
                    # Calculate RR for range trade
                    risk = current_price - zone_bottom
                    reward = zone_top - current_price
                    
                    if risk > 0:
                        rr_ratio = reward / risk
                        return {
                            "base": round(rr_ratio, 1),
                            "p_succeed": 0.45,  # Conservative for range trades
                            "method": "range: entry near zone bottom; targets=zone top; stop=zone bottom"
                        }
        
        return {
            "base": 1.0,
            "p_succeed": 0.3,
            "method": "default_estimate"
        }
    
    def _calculate_targets(self, overview_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate trading targets"""
        current_position = overview_analysis.get('current_position', '')
        key_levels = overview_analysis.get('key_levels', {})
        zones = key_levels.get('zones', [])
        
        targets = []
        
        if current_position == 'inside_zone' and zones:
            current_price = self.current_price
            current_zone = None
            for zone in zones:
                if zone.get('bottom', 0) <= current_price <= zone.get('top', 0):
                    current_zone = zone
                    break
            
            if current_zone:
                zone_top = current_zone.get('top', 0)
                zone_bottom = current_zone.get('bottom', 0)
                
                # T1: Zone top
                targets.append({
                    "level": zone_top,
                    "weight": 0.5,
                    "kind": "in-zone-cap"
                })
                
                # T2: Next zone bottom (if exists)
                other_zones = [z for z in zones if z.get('id') != current_zone.get('id')]
                zones_above = [z for z in other_zones if z.get('bottom', 0) > zone_top]
                if zones_above:
                    next_zone_bottom = min(z.get('bottom', 0) for z in zones_above)
                    targets.append({
                        "level": next_zone_bottom,
                        "weight": 0.5,
                        "kind": "next-zone-bottom"
                    })
        
        return targets
    
    def _calculate_entry_hint(self, overview_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate entry hint"""
        current_position = overview_analysis.get('current_position', '')
        key_levels = overview_analysis.get('key_levels', {})
        zones = key_levels.get('zones', [])
        
        # Get ATR for tolerance calculation
        atr = self._calculate_atr(14) or 0
        
        if current_position == 'inside_zone' and zones:
            current_price = self.current_price
            for zone in zones:
                if zone.get('bottom', 0) <= current_price <= zone.get('top', 0):
                    zone_bottom = zone.get('bottom', 0)
                    # Prefer entry near zone bottom
                    preferred_entry = zone_bottom + (current_price - zone_bottom) * 0.3
                    # ATR-aware tolerance
                    tolerance = max(0.01 * self.current_price, 0.5 * atr)
                    return {
                        "preferred": round(preferred_entry, 3),
                        "tolerance": round(tolerance, 6)
                    }
        
        # ATR-aware tolerance
        tolerance = max(0.01 * self.current_price, 0.5 * atr)
        return {
            "preferred": self.current_price,
            "tolerance": round(tolerance, 6)
        }
    
    def _calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range"""
        ohlcv = self.ohlc_data.get('ohlcv', [])
        if len(ohlcv) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(ohlcv)):
            high = ohlcv[i][2]
            low = ohlcv[i][3]
            prev_close = ohlcv[i-1][4]
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if len(true_ranges) < period:
            return 0.0
        
        # Calculate ATR as simple moving average of true ranges
        recent_trs = true_ranges[-period:]
        return sum(recent_trs) / len(recent_trs)
    
    def _calculate_risk_metrics(self, overview_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics including suggested stop"""
        current_position = overview_analysis.get('current_position', '')
        key_levels = overview_analysis.get('key_levels', {})
        zones = key_levels.get('zones', [])
        
        # Calculate real ATR
        atr_value = self._calculate_atr(14)
        suggested_stop = None
        
        if current_position == 'inside_zone' and zones:
            current_price = self.current_price
            for zone in zones:
                if zone.get('bottom', 0) <= current_price <= zone.get('top', 0):
                    zone_bottom = zone.get('bottom', 0)
                    # ATR-aware stop: zone bottom - max(0.5*ATR, 0.3% of price)
                    suggested_stop = round(zone_bottom - max(0.5 * atr_value, 0.003 * self.current_price), 6)
                    break
        
        return {
            "atr_n": 14,
            "atr_value": round(atr_value, 6),
            "suggested_stop": suggested_stop,
            "invalidation_rule": "daily_close_below_zone_bottom",
            "position_size_hint": 0.5
        }
    
    def collect_analysis_data(self) -> Dict[str, Any]:
        """Main method to collect all analysis data"""
        logger.info("Starting Stage 6A data collection...")
        
        # Calculate all data
        element_sequences, all_events = self._calculate_element_sequences()
        volume_analysis = self._calculate_volume_analysis(element_sequences)
        volatility_analysis = self._calculate_volatility()
        pattern_start, pattern_end = self._get_pattern_formation_dates()
        
        # Get global and recent significant events from pre-computed all_events
        global_events, recent_events = self._get_global_and_recent_events_from_all(all_events)
        
        # Calculate overview analysis from element data
        overview_analysis = self._calculate_overview_analysis(element_sequences, global_events, recent_events)
        
        # Split symbol into base and quote
        full_symbol = self.ohlc_data.get('symbol', '')
        if '/' in full_symbol:
            symbol, quote_asset = full_symbol.split('/')
        else:
            symbol = full_symbol
            quote_asset = None
        
        # Build analysis data
        analysis_data = {
            "record_kind": "analysis",
            "stage": "s6a",
            "symbol": symbol,
            "quote_asset": quote_asset,
            "timeframe": self.ohlc_data.get('timeframe', None),
            "pipeline": "vision",
            "source_tags": ["chart", "vision"],
            "content_hash": None,  # TODO: Calculate hash
            "trader_handle": None,  # Missing - flagged
            "venue": "hyperliquid",
            "leverage_type": "1x",
            
            # Temporal Context
            "created_at": datetime.now(timezone.utc).isoformat(),
            "chart_timeframe": self.ohlc_data.get('timeframe', None),
            "pattern_formation_start": pattern_start,
            "pattern_formation_end": pattern_end,
            "current_price": self.current_price,
            "breakout_status": overview_analysis.get('breakout_status', 'pending'),
            "execution_readiness": self._calculate_execution_readiness(overview_analysis),
            
            # Market Context
            "market_regime": None,  # TBD
            "corr_group": "alts",
            "vol_bucket": volatility_analysis.get('volatility_label', 'unknown'),
            
            # Token Context
            "token_context": {
                "marketcap": None,  # Missing - flagged
                "volume_analysis": volume_analysis,
                "volatility_analysis": volatility_analysis,
                "token_health": None,  # Future
                "social_data": None  # Future
            },
            
            # Pattern Analysis (LLM will fill these)
            "pattern_type": None,  # LLM
            "pattern_quality": None,  # LLM
            "market_structure": None,  # LLM
            "strategy_dsl": None,  # LLM
            
            # Price Position Analysis - IMPROVED STRUCTURE
            "price_position_analysis": {
                "global_significant_events": global_events,
                "recent_significant_events": recent_events,
                "elements": element_sequences,
                "breakout_confirmation": overview_analysis.get('breakout_confirmation', False),
                "retest_status": "none",  # TODO: Implement retest detection
                "volume_confirmation": overview_analysis.get('volume_confirmation', False),
                "momentum_direction": overview_analysis.get('momentum_direction', 'unknown'),
                "key_levels": overview_analysis.get('key_levels', {}),
                "current_position": overview_analysis.get('current_position', 'unknown'),
                "recent_activity_summary": overview_analysis.get('recent_activity_summary', {})
            },
            
            # Timeframe Analysis (LLM will fill these)
            "timeframe_analysis": {
                "primary_timeframe": self.ohlc_data.get('timeframe', None),
                "lower_timeframe_analysis": None,  # LLM
                "higher_timeframe_context": None,  # LLM
                "timeframe_alignment": None  # LLM
            },
            
            # Plan Status
            "plan_status": "pending",  # TODO: Implement plan status logic
            "entry_time": None,  # TODO: Calculate entry time
            "side": self._calculate_side(overview_analysis),
            "invalidation_levels": self._calculate_invalidation_levels(overview_analysis),
            "rr_estimate": self._calculate_rr_estimate(overview_analysis),
            "targets": self._calculate_targets(overview_analysis),
            "entry_hint": self._calculate_entry_hint(overview_analysis),
            
            # Derived Trading Intelligence
            "derived": {
                "htf": {
                    "timeframe": "1W",
                    "trend": "down"  # TODO: Calculate from higher timeframe
                },
                "pattern": {
                    "type": "range_with_diagonal_breakouts",  # TODO: LLM classification
                    "quality": 0.62  # TODO: Calculate from volume/price action
                },
                "state_machine": self._calculate_state_machine_mode(overview_analysis, volume_analysis),
                "levels": self._calculate_derived_levels(overview_analysis),
                "risk": self._calculate_risk_metrics(overview_analysis)
            }
            
        }
        
        # Log missing data
        if self.missing_data:
            logger.warning(f"Missing data flagged: {self.missing_data}")
            analysis_data["missing_data_flags"] = self.missing_data
        
        logger.info("Stage 6A data collection completed")
        return analysis_data

def main():
    """Main function to run Stage 6A"""
    # Load Stage 5A results
    stage5a_path = Path("stage5a_consolidated_results.json")
    
    if not stage5a_path.exists():
        logger.error(f"Stage 5A results not found: {stage5a_path}")
        return
    
    with open(stage5a_path, 'r') as f:
        stage5a_data = json.load(f)
    
    # Run Stage 6A
    collector = Stage6ADataCollector(stage5a_data)
    analysis_data = collector.collect_analysis_data()
    
    # Save results
    output_path = Path("stage6a_analysis_results.json")
    with open(output_path, 'w') as f:
        json.dump(analysis_data, f, indent=2)
    
    logger.info(f"Stage 6A results saved to: {output_path}")
    
    # Print summary
    print(f"\nStage 6A Analysis Summary:")
    print(f"Symbol: {analysis_data.get('symbol', 'Unknown')}")
    print(f"Current Price: {analysis_data.get('current_price', 'Unknown')}")
    print(f"Current Position: {analysis_data.get('price_position_analysis', {}).get('current_position', 'Unknown')}")
    print(f"Execution Readiness: {analysis_data.get('execution_readiness', 'Unknown')}")
    print(f"Breakout Status: {analysis_data.get('breakout_status', 'Unknown')}")
    # Count elements (excluding the analysis metadata fields)
    analysis_fields = {'breakout_confirmation', 'retest_status', 'volume_confirmation', 'momentum_direction'}
    element_count = len([k for k in analysis_data.get('price_position_analysis', {}).get('elements', {}).keys() if k not in analysis_fields])
    print(f"Elements Analyzed: {element_count}")
    
    if analysis_data.get('missing_data_flags'):
        print(f"Missing Data: {analysis_data['missing_data_flags']}")

if __name__ == "__main__":
    main()
