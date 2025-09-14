#!/usr/bin/env python3
"""
Stage 4: Calibration & Mapping

This stage handles:
- 4A: Axis Context and Date Range (with dynamic OHLC fetching)
- 4B: Horizontal Anchor Tags (price labels)
- 4C: Candle Mapping (wick detection)
- 4Ci: Month Mapping for peak columns
- 4D: Dual Calibration (price + temporal formulas)
"""

import asyncio
import json
import logging
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import cv2
import numpy as np
from PIL import Image
import base64
import io

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Stage4Detector:
    """Stage 4: Calibration & Mapping"""
    
    def __init__(self, detector):
        """Initialize with the element detector."""
        self.detector = detector
    
    async def run_stage4(self, image_path: str, grid_image_path: str, grid_metadata: Dict[str, Any], 
                         stage2_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Stage 4: Complete calibration and mapping pipeline.
        
        Args:
            image_path: Path to original chart image
            grid_image_path: Path to grid overlay image
            grid_metadata: Grid metadata from Stage 2
            stage2_results: Results from Stage 2
            
        Returns:
            Dict containing all Stage 4 results
        """
        try:
            print("🎯 STAGE 4: CALIBRATION & MAPPING")
            print("=" * 50)
            
            # Initialize results structure
            stage4_results = {
                "stage4a_results": {},
                "stage4b_results": {},
                "stage4c_results": {},
                "stage4ci_results": {},
                "stage4d_results": {},
                "metadata": {
                    "image_path": image_path,
                    "grid_image_path": grid_image_path,
                    "grid_metadata": grid_metadata
                }
            }
            
            # Stage 4A: Axis Context and Date Range
            print("\n📊 Stage 4A: Axis Context and Date Range")
            stage4a_results = await self._run_stage4a(image_path)
            stage4_results["stage4a_results"] = stage4a_results
            
            # Stage 4B: Horizontal Anchor Tags
            print("\n🏷️ Stage 4B: Horizontal Anchor Tags")
            stage4b_results = await self._run_stage4b(grid_image_path, grid_metadata, stage2_results)
            stage4_results["stage4b_results"] = stage4b_results
            
            # Stage 4C: Candle Mapping (Wick Detection)
            print("\n🕯️ Stage 4C: Candle Mapping - Wick Detection")
            stage4c_results = await self._run_stage4c(image_path, grid_metadata, stage2_results)
            stage4_results["stage4c_results"] = stage4c_results
            
            # Stage 4Ci: Month Mapping for Peak Columns
            print("\n📅 Stage 4Ci: Month Mapping for Peak Columns")
            stage4ci_results = await self._run_stage4ci(grid_image_path, stage4c_results)
            stage4_results["stage4ci_results"] = stage4ci_results
            
            # Stage 4D: Dual Calibration
            print("\n🔧 Stage 4D: Dual Calibration (Price + Temporal)")
            stage4d_results = await self._run_stage4d(stage4b_results, stage4c_results, 
                                                     stage4ci_results, stage4a_results)
            stage4_results["stage4d_results"] = stage4d_results
            
            # Save complete results
            with open('stage4_results.json', 'w') as f:
                json.dump(stage4_results, f, indent=2)
            
            print("\n✅ Stage 4 completed successfully!")
            return stage4_results
            
        except Exception as e:
            print(f"❌ Stage 4 failed: {e}")
            logger.error(f"Stage 4 error: {e}", exc_info=True)
            raise
    
    async def _run_stage4a(self, image_path: str) -> Dict[str, Any]:
        """Stage 4A: Axis Context and Date Range with dynamic OHLC fetching."""
        try:
            # Load Stage 4A prompt
            with open("prompts/pipeline_prompts/stage4a_axis_full.md", "r") as f:
                stage4a_prompt = f.read()
            
            # Run Stage 4A
            stage4a_raw = await self.detector.detect_elements(image_path, stage4a_prompt)
            
            # Parse response
            stage4a_result = self._parse_kv_response(stage4a_raw)
            
            print(f"  ✅ Axis side: {stage4a_result.get('axis_side')}")
            print(f"  ✅ Symbol: {stage4a_result.get('symbol')}")
            print(f"  ✅ Timeframe: {stage4a_result.get('timeframe')}")
            print(f"  ✅ Candle count: {stage4a_result.get('candle_count')}")
            
            # Dynamic OHLC fetching
            ohlc_data = await self._fetch_dynamic_ohlc(stage4a_result)
            stage4a_result['ohlc_data'] = ohlc_data
            
            return stage4a_result
            
        except Exception as e:
            print(f"❌ Stage 4A failed: {e}")
            return {}
    
    async def _run_stage4b(self, grid_image_path: str, grid_metadata: Dict[str, Any], 
                           stage2_results: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4B: Horizontal Anchor Tags (price labels)."""
        try:
            # Load Stage 4B prompt
            with open("prompts/pipeline_prompts/stage4b_anchor_only.md", "r") as f:
                stage4b_prompt = f.read()
            
            # Run Stage 4B
            stage4b_raw = await self.detector.detect_elements(grid_image_path, stage4b_prompt)
            
            # Parse anchors
            anchors = self._parse_anchors(stage4b_raw)
            print(f"  ✅ Anchors detected: {len(anchors)}")
            
            # Resolve anchor y_px using Stage 2Di results
            anchor_points = self._resolve_anchor_points(anchors, grid_metadata, stage2_results)
            print(f"  ✅ Anchor points resolved: {len(anchor_points)}")
            
            return {
                "anchors": anchors,
                "anchor_points": anchor_points
            }
            
        except Exception as e:
            print(f"❌ Stage 4B failed: {e}")
            return {}
    
    async def _run_stage4c(self, image_path: str, grid_metadata: Dict[str, Any], 
                           stage2_results: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4C: Candle Mapping - Wick Detection."""
        try:
            # Extract data from Stage 2
            stage2a_data = stage2_results.get('stage2a_results', {})
            stage2di_results = stage2_results.get('stage2di_results', [])
            stage2diii_results = stage2_results.get('stage2diii_results', [])
            
            # Build exclusion lists
            horizontals_y_px = []
            for det in stage2di_results:
                ypix = det.get('coordinates', {}).get('y_pixel')
                if isinstance(ypix, (int, float)):
                    horizontals_y_px.append(int(round(ypix)))
            
            zone_boundaries_y_px = []
            for z in stage2diii_results:
                for key in ('y_top_px', 'y_bottom_px'):
                    val = z.get(key)
                    if isinstance(val, (int, float)):
                        zone_boundaries_y_px.append(int(round(val)))
            
            # Determine dynamic stop-before-column from arrows
            stop_before_column_ord = ord('H') + 1
            for arr in stage2a_data.get('arrows', []):
                start = arr.get('start', '')
                if isinstance(start, str) and len(start) == 2 and start[0].isalpha():
                    arrow_col_ord = ord(start[0].upper())
                    stop_before_column_ord = min(stop_before_column_ord, arrow_col_ord)
            
            print(f"  🔍 Scanning columns B through {chr(stop_before_column_ord - 1)}")
            
            # Run wick detection
            candle_map = self._detect_wicks(image_path, grid_metadata, horizontals_y_px, 
                                         zone_boundaries_y_px, stop_before_column_ord)
            
            # Save debug images
            self._save_wick_debug_images(candle_map)
            
            print(f"  ✅ Wick detection completed: {len(candle_map['columns_scanned'])} columns")
            print(f"  ✅ Top wicks: {len(candle_map['top_wicks'])}")
            print(f"  ✅ Bottom wicks: {len(candle_map['bottom_wicks'])}")
            
            return candle_map
            
        except Exception as e:
            print(f"❌ Stage 4C failed: {e}")
            return {}
    
    async def _run_stage4ci(self, grid_image_path: str, stage4c_results: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4Ci: Month Mapping for Peak Columns."""
        try:
            # Check if we have peak column information
            if 'peak_high_column' not in stage4c_results or 'peak_low_column' not in stage4c_results:
                print("  ⚠️ No peak column information available")
                return {}
            
            peak_high_col = stage4c_results['peak_high_column']
            peak_low_col = stage4c_results['peak_low_column']
            
            print(f"  🎯 Using peak columns: {peak_high_col} (high), {peak_low_col} (low)")
            
            # Load and customize prompt
            with open("prompts/pipeline_prompts/stage4ci_month_mapping.md", "r") as f:
                stage4ci_prompt = f.read()
            
            # Replace placeholders
            stage4ci_prompt = stage4ci_prompt.replace("{HIGH_COL}", peak_high_col)
            stage4ci_prompt = stage4ci_prompt.replace("{LOW_COL}", peak_low_col)
            
            # Run Stage 4Ci
            stage4ci_raw = await self.detector.detect_elements(grid_image_path, stage4ci_prompt)
            
            # Parse month mapping
            month_mapping = self._parse_month_mapping(stage4ci_raw)
            
            print(f"  ✅ Month mapping detected:")
            for col, month_range in month_mapping.items():
                print(f"    - {col}: {month_range}")
            
            return month_mapping
            
        except Exception as e:
            print(f"❌ Stage 4Ci failed: {e}")
            return {}
    
    async def _run_stage4d(self, stage4b_results: Dict[str, Any], stage4c_results: Dict[str, Any],
                           stage4ci_results: Dict[str, Any], stage4a_results: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4D: Dual Calibration (Price + Temporal)."""
        try:
            # Initialize calibration structure
            calibration = {
                "price_calibration": {"alpha": None, "beta": None, "calibration_points": []},
                "temporal_calibration": {"gamma": None, "delta": None, "calibration_points": []},
                "metadata": {"anchors_used": 0, "wicks_used": 0, "ohlc_periods": []}
            }
            
            print("  🔧 Starting dual calibration process...")
            
            # Phase 1: Price Calibration
            print("  📊 Phase 1: Price Calibration")
            price_calib = self._calculate_price_calibration(stage4b_results, stage4c_results, 
                                                         stage4ci_results, stage4a_results)
            if price_calib:
                calibration['price_calibration'] = price_calib
                calibration['metadata']['anchors_used'] = len(stage4b_results.get('anchor_points', []))
                calibration['metadata']['wicks_used'] = len(price_calib.get('calibration_points', []))
            
            # Phase 2: Temporal Calibration
            print("  ⏰ Phase 2: Temporal Calibration")
            temporal_calib = self._calculate_temporal_calibration(stage4c_results, stage4ci_results, 
                                                               stage4a_results)
            if temporal_calib:
                calibration['temporal_calibration'] = temporal_calib
            
            # Update metadata
            calibration['metadata']['ohlc_periods'] = list(stage4ci_results.values())
            
            # Save calibration
            with open('stage4_calibration.json', 'w') as f:
                json.dump(calibration, f, indent=2)
            
            print("  ✅ Dual calibration completed and saved")
            return calibration
            
        except Exception as e:
            print(f"❌ Stage 4D failed: {e}")
            return {}
    
    async def _fetch_dynamic_ohlc(self, stage4a_result: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch dynamic OHLC data based on Stage 4A results."""
        try:
            import ccxt
            from datetime import datetime, timedelta
            
            # Extract parameters
            symbol_raw = stage4a_result.get('symbol', '')
            timeframe = stage4a_result.get('timeframe', '1d')
            candle_count = int(stage4a_result.get('candle_count', '150'))
            
            # Better symbol selection - check what Binance offers for KAITO
            if 'KAITO' in symbol_raw.upper():
                print(f"    🔍 Checking available KAITO markets on Binance...")
                try:
                    # Initialize exchange first for market checking
                    temp_exchange = ccxt.binance({
                        'enableRateLimit': True,
                        'options': {'defaultType': 'spot'}
                    })
                    # Get available markets for KAITO
                    markets = temp_exchange.load_markets()
                    kaito_markets = [k for k in markets.keys() if 'KAITO' in k.upper()]
                    
                    if kaito_markets:
                        print(f"    📊 Available KAITO markets: {kaito_markets}")
                        # Prefer USDT (most liquid), then USDC, then others
                        if 'KAITO/USDT' in kaito_markets:
                            symbol = 'KAITO/USDT'
                            print(f"    ✅ Selected KAITO/USDT (most liquid)")
                        elif 'KAITO/USDC' in kaito_markets:
                            symbol = 'KAITO/USDC'
                            print(f"    ✅ Selected KAITO/USDC")
                        else:
                            symbol = kaito_markets[0]  # Use first available
                            print(f"    ✅ Selected {symbol}")
                    else:
                        print(f"    ⚠️ No KAITO markets found, using fallback")
                        symbol = 'KAITO/USDT'  # Fallback
                except Exception as e:
                    print(f"    ⚠️ Could not check markets: {e}")
                    symbol = 'KAITO/USDT'  # Fallback
            else:
                symbol = symbol_raw.replace(' ', '').replace('/', '')
            
            print(f"    🔧 Final symbol: '{symbol}'")
            
            print(f"    🎯 Fetching {candle_count} {timeframe} candles for {symbol}")
            
            # Initialize exchange (Binance) for OHLC fetching
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            
            # Calculate date range
            end_date = datetime.now()
            if timeframe == '1d':
                start_date = end_date - timedelta(days=candle_count)
            elif timeframe == '4h':
                start_date = end_date - timedelta(hours=4*candle_count)
            elif timeframe == '1h':
                start_date = end_date - timedelta(hours=candle_count)
            else:
                start_date = end_date - timedelta(days=candle_count)
            
            print(f"    📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Map timeframe to Binance format
            binance_timeframe = timeframe
            if timeframe == '1D':
                binance_timeframe = '1d'  # Binance uses lowercase
            elif timeframe == '4H':
                binance_timeframe = '4h'
            elif timeframe == '1H':
                binance_timeframe = '1h'
            
            print(f"    🔧 Timeframe mapping: {timeframe} → {binance_timeframe}")
            
            # Fetch OHLC data (ccxt.binance() is synchronous)
            ohlcv = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=binance_timeframe,
                since=int(start_date.timestamp() * 1000),
                limit=candle_count
            )
            
            if ohlcv:
                ohlc_data = {
                    "symbol": symbol,
                    "exchange": "binance",
                    "timeframe": timeframe,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "price_range": {
                        "min": min([record[3] for record in ohlcv]),
                        "max": max([record[2] for record in ohlcv])
                    },
                    "records_count": len(ohlcv),
                    "ohlcv": ohlcv
                }
                
                # Save dynamic OHLC data
                with open('dynamic_ohlc_data.json', 'w') as f:
                    json.dump(ohlc_data, f, indent=2)
                
                print(f"    ✅ Dynamic OHLC data fetched: {len(ohlcv)} candles")
                print(f"    💰 Price range: {ohlc_data['price_range']['min']:.6f} to {ohlc_data['price_range']['max']:.6f}")
                
                return ohlc_data
            else:
                print("    ⚠️ No OHLC data fetched")
                return {}
                
        except Exception as e:
            print(f"    ⚠️ Dynamic OHLC fetching failed: {e}")
            return {}
    
    def _parse_kv_response(self, response: Any) -> Dict[str, str]:
        """Parse key-value response from LLM."""
        out = {}
        if isinstance(response, dict):
            raw_response = response.get('raw_response', '')
            if raw_response.startswith('```'):
                lines = raw_response.split('\n')
                parsed_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        parsed_lines.append(line)
                raw_response = '\n'.join(parsed_lines)
            
            for ln in raw_response.splitlines():
                ln = ln.strip()
                if not ln or ':' not in ln:
                    continue
                k, v = ln.split(':', 1)
                out[k.strip().lower()] = v.strip()
        else:
            for ln in str(response or '').splitlines():
                ln = ln.strip()
                if not ln or ':' not in ln:
                    continue
                k, v = ln.split(':', 1)
                out[k.strip().lower()] = v.strip()
        return out
    
    def _parse_anchors(self, response: Any) -> List[Dict[str, Any]]:
        """Parse anchor tags from LLM response."""
        out = []
        if isinstance(response, dict):
            raw_response = response.get('raw_response', '')
            if raw_response.startswith('```'):
                lines = raw_response.split('\n')
                parsed_lines = []
                in_code_block = False
                for line in lines:
                    if line.startswith('```'):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        parsed_lines.append(line)
                raw_response = '\n'.join(parsed_lines)
            
            lines = [ln.strip() for ln in raw_response.splitlines() if ln.strip()]
            kv = {}
            for ln in lines:
                if ':' in ln:
                    k, v = ln.split(':', 1)
                    kv[k.strip().lower()] = v.strip()
            
            try:
                cnt = int(kv.get('anchors_count', '0'))
            except Exception:
                cnt = 0
            
            for i in range(1, cnt+1):
                t = kv.get(f'anchor_{i}_text')
                g = kv.get(f'anchor_{i}_grid_line')
                if t and g:
                    out.append({"text": str(t).strip(), "grid_line": int(str(g).strip())})
        else:
            lines = [ln.strip() for ln in str(response or '').splitlines() if ln.strip()]
            kv = {}
            for ln in lines:
                if ':' in ln:
                    k, v = ln.split(':', 1)
                    kv[k.strip().lower()] = v.strip()
            
            try:
                cnt = int(kv.get('anchors_count', '0'))
            except Exception:
                cnt = 0
            
            for i in range(1, cnt+1):
                t = kv.get(f'anchor_{i}_text')
                g = kv.get(f'anchor_{i}_grid_line')
                if t and g:
                    try:
                        out.append({"text": t, "grid_line": int(g)})
                    except Exception:
                        pass
        return out
    
    def _resolve_anchor_points(self, anchors: List[Dict[str, Any]], grid_metadata: Dict[str, Any],
                              stage2_results: Dict[str, Any]) -> List[Tuple[int, float]]:
        """Resolve anchor y_px using Stage 2Di results."""
        try:
            padding = int(grid_metadata['cell_padding'])
            cell_h = float(grid_metadata['cell_height_px'])
            grid_rows = int(grid_metadata['grid_rows'])
            
            # Get horizontal lines from Stage 2Di
            horizontals_exact = []
            stage2di_results = stage2_results.get('stage2di_results', [])
            for det in stage2di_results:
                ypix = det.get('coordinates', {}).get('y_pixel')
                if isinstance(ypix, (int, float)):
                    horizontals_exact.append(int(round(ypix)))
            
            # Parse price from anchor text
            def parse_price(s):
                try:
                    m = re.findall(r"[0-9]+(?:\.[0-9]+)?", str(s))
                    return float(m[0]) if m else None
                except Exception:
                    return None
            
            anchor_points = []
            for a in anchors:
                row = int(a['grid_line'])
                # Compute pixel band for that row
                y_top = int(round(padding + (grid_rows - row) * cell_h))
                y_bottom = int(round(padding + (grid_rows - row + 1) * cell_h))
                # Find any horizontal with y in this band
                matches = [y for y in horizontals_exact if y_top <= y <= y_bottom]
                if not matches:
                    continue
                # If multiple, choose the one closest to mid-band
                mid = (y_top + y_bottom) // 2
                y_anchor = min(matches, key=lambda y: abs(y - mid))
                price_val = parse_price(a['text'])
                if price_val is not None:
                    anchor_points.append((y_anchor, price_val))
            
            return anchor_points
            
        except Exception as e:
            print(f"    ❌ Anchor resolution failed: {e}")
            return []
    
    def _detect_wicks(self, image_path: str, grid_metadata: Dict[str, Any], 
                      horizontals_y_px: List[int], zone_boundaries_y_px: List[int],
                      stop_before_column_ord: int) -> Dict[str, Any]:
        """Detect wick highs and lows in chart columns."""
        try:
            padding = int(grid_metadata['cell_padding'])
            cell_w = float(grid_metadata['cell_width_px'])
            cell_h = float(grid_metadata['cell_height_px'])
            grid_rows = int(grid_metadata['grid_rows'])
            
            full_bgr = cv2.imread(image_path)
            H_img, W_img = full_bgr.shape[:2]
            
            def crop_cell(col_letter: str, row_idx: int):
                col_zero = ord(col_letter.upper()) - ord('A')
                x0 = int(round(padding + col_zero * cell_w))
                x1 = int(round(padding + (col_zero + 1) * cell_w))
                y0 = int(round(padding + (grid_rows - row_idx) * cell_h))
                y1 = int(round(padding + (grid_rows - row_idx + 1) * cell_h))
                crop = full_bgr[max(0,y0):min(H_img,y1), max(0,x0):min(W_img,x1)]
                return x0, y0, x1, y1, crop
            
            def disallowed(y_abs: int) -> bool:
                horizontal_margin = 2
                zone_margin = 12
                
                for y in horizontals_y_px:
                    if abs(y_abs - y) <= horizontal_margin:
                        return True
                for y in zone_boundaries_y_px:
                    if abs(y_abs - y) <= zone_margin:
                        return True
                return False
            
            candle_map = {"columns_scanned": [], "top_wicks": {}, "bottom_wicks": {}, "debug_saved": True}
            
            # Find peak columns first
            temp_highs = {}
            temp_lows = {}
            
            for col_ord in range(ord('B'), stop_before_column_ord):
                col_letter = chr(col_ord)
                
                # Quick scan for this column
                for row in range(6, 0, -1):
                    x0, y0, x1, y1, crop = crop_cell(col_letter, row)
                    if crop.size == 0:
                        continue
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray, 50, 150)
                    
                    # Skip first 150px in row 6 (same logic as detailed scan)
                    skip_top = 150 if row == 6 else 0
                    if row == 6:
                        # Check if there are edges in the next 50px after skip_top
                        band = edges[min(edges.shape[0], skip_top):min(edges.shape[0], skip_top+50), :]
                        if band.size > 0 and np.sum(band) > 0:
                            # Expect NO edges in the next 50px. If present, try next row.
                            continue
                    
                    ys, xs = np.where(edges == 255)
                    if ys.size == 0:
                        continue
                    
                    # Filter out edges in the skipped region
                    valid_ys = [y for y in ys if y >= skip_top]
                    if not valid_ys:
                        continue
                    
                    # Found edges, record y position
                    y_abs = y0 + int(min(valid_ys))
                    if col_letter not in temp_highs or y_abs < temp_highs[col_letter]:
                        temp_highs[col_letter] = y_abs
                    break
                
                for row in range(1, 7):
                    x0, y0, x1, y1, crop = crop_cell(col_letter, row)
                    if crop.size == 0:
                        continue
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray, 50, 150)
                    ys, xs = np.where(edges == 255)
                    if ys.size > 0:
                        y_abs = y0 + int(max(ys))
                        if col_letter not in temp_lows or y_abs > temp_lows[col_letter]:
                            temp_lows[col_letter] = y_abs
                        break
            
            # Find peak columns
            if temp_highs:
                peak_high_col = min(temp_highs.items(), key=lambda x: x[1])[0]
                peak_high_y = temp_highs[peak_high_col]
            else:
                peak_high_col = 'C'
                peak_high_y = 200
            
            if temp_lows:
                peak_low_col = max(temp_lows.items(), key=lambda x: x[1])[0]
                peak_low_y = temp_lows[peak_low_col]
            else:
                peak_low_col = 'B'
                peak_low_y = 800
            
            print(f"    🔍 Peak column detection:")
            print(f"      - Temp highs: {temp_highs}")
            print(f"      - Temp lows: {temp_lows}")
            print(f"      - Selected high: {peak_high_col} @ y={peak_high_y}")
            print(f"      - Selected low: {peak_low_col} @ y={peak_low_y}")
            
            # Debug: show what columns we're actually scanning
            print(f"    🔍 Columns scanned in quick scan: {[chr(ord('B') + i) for i in range(stop_before_column_ord - ord('B'))]}")
            
            peak_columns = [peak_high_col, peak_low_col]
            print(f"    🎯 Peak columns: {peak_high_col} (high at y={peak_high_y}), {peak_low_col} (low at y={peak_low_y})")
            
            # Only scan the peak columns
            for col_letter in peak_columns:
                candle_map['columns_scanned'].append(col_letter)
                
                # TOP SCAN rows 6->1
                found_top = False
                for row in range(6, 0, -1):
                    x0, y0, x1, y1, crop = crop_cell(col_letter, row)
                    if crop.size == 0:
                        continue
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray, 50, 150)
                    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                    skip_top = 150 if row == 6 else 0
                    if row == 6:
                        # Check if there are edges in the next 50px after skip_top
                        band = edges[min(edges.shape[0], skip_top):min(edges.shape[0], skip_top+50), :]
                        if band.size > 0 and np.sum(band) > 0:
                            # Expect NO edges in the next 50px. If present, try next row.
                            continue
                    ys, xs = np.where(edges == 255)
                    if ys.size == 0:
                        continue
                    valid = []
                    for iy, ix in zip(ys, xs):
                        if iy < skip_top:
                            continue
                        y_abs = y0 + int(iy)
                        if disallowed(y_abs):
                            continue
                        # Vertical-dominant filter: reject mostly horizontal edges
                        gx = float(abs(grad_x[iy, ix]))
                        gy = float(abs(grad_y[iy, ix]))
                        if gx >= max(1.0, gy) * 0.8:  # require gy to dominate
                            continue
                        valid.append((iy, ix))
                    if not valid:
                        continue
                    iy, ix = min(valid, key=lambda t: t[0])
                    candle_map['top_wicks'][col_letter] = {"row": row, "x_px_abs": int(x0 + ix), "y_px_abs": int(y0 + iy)}
                    found_top = True
                    break
                
                # BOTTOM SCAN rows 1->6
                found_bottom = False
                for row in range(1, 7):
                    x0, y0, x1, y1, crop = crop_cell(col_letter, row)
                    if crop.size == 0:
                        continue
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray, 50, 150)
                    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
                    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
                    skip_bottom = 150 if row == 1 else 0
                    ys, xs = np.where(edges == 255)
                    if ys.size == 0:
                        continue
                    valid = []
                    for iy, ix in zip(ys, xs):
                        if skip_bottom and iy >= (edges.shape[0] - skip_bottom):
                            continue
                        y_abs = y0 + int(iy)
                        if disallowed(y_abs):
                            continue
                        gx = float(abs(grad_x[iy, ix]))
                        gy = float(abs(grad_y[iy, ix]))
                        if gx >= max(1.0, gy) * 0.8:
                            continue
                        valid.append((iy, ix))
                    if not valid:
                        continue
                    iy, ix = max(valid, key=lambda t: t[0])
                    candle_map['bottom_wicks'][col_letter] = {"row": row, "x_px_abs": int(x0 + ix), "y_px_abs": int(y0 + iy)}
                    found_bottom = True
                    break
            
            # Store peak columns
            candle_map['peak_high_column'] = peak_high_col
            candle_map['peak_low_column'] = peak_low_col
            
            return candle_map
            
        except Exception as e:
            print(f"    ❌ Wick detection failed: {e}")
            return {"columns_scanned": [], "top_wicks": {}, "bottom_wicks": {}, "debug_saved": False}
    
    def _save_wick_debug_images(self, candle_map: Dict[str, Any]):
        """Save debug images for wick detection."""
        try:
            debug_dir = Path('stage4_debug')
            debug_dir.mkdir(exist_ok=True)
            
            # Save candle mapping data
            with open(debug_dir / 'candle_mapping.json', 'w') as f:
                json.dump(candle_map, f, indent=2)
            
            print(f"    💾 Debug data saved to: {debug_dir}")
            
        except Exception as e:
            print(f"    ⚠️ Could not save debug images: {e}")
    
    def _parse_month_mapping(self, response: Any) -> Dict[str, str]:
        """Parse month mapping from LLM response."""
        out = {}
        if isinstance(response, dict):
            raw_response = response.get('raw_response', '')
            lines = raw_response.splitlines()
        else:
            lines = str(response or '').splitlines()
        
        for ln in lines:
            ln = ln.strip()
            if not ln or '=' not in ln:
                continue
            if '=' in ln:
                k, v = ln.split('=', 1)
                out[k.strip()] = v.strip()
        return out
    
    def _calculate_price_calibration(self, stage4b_results: Dict[str, Any], stage4c_results: Dict[str, Any],
                                   stage4ci_results: Dict[str, Any], stage4a_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate price calibration formula: price = α*y + β."""
        try:
            anchor_points = stage4b_results.get('anchor_points', [])
            candle_map = stage4c_results
            month_mapping = stage4ci_results
            
            if not anchor_points or 'peak_high_column' not in candle_map or 'peak_low_column' not in candle_map:
                return None
            
            # Get wick coordinates
            peak_high_col = candle_map['peak_high_column']
            peak_low_col = candle_map['peak_low_column']
            wick_high = candle_map['top_wicks'].get(peak_high_col)
            wick_low = candle_map['bottom_wicks'].get(peak_low_col)
            
            if not wick_high or not wick_low:
                return None
            
            # Build calibration points
            calibration_points = []
            
            # Add anchor points
            for y_anchor, price_anchor in anchor_points:
                calibration_points.append({
                    "y": y_anchor,
                    "price": price_anchor,
                    "source": "anchor"
                })
            
            # Add wick points with actual OHLC prices
            if month_mapping and 'ohlc_data' in stage4a_results:
                ohlc_data = stage4a_results['ohlc_data']
                
                # Get actual OHLC prices for the wick periods
                high_price = self._get_ohlc_price_for_wick(peak_high_col, month_mapping, ohlc_data, 'high')
                low_price = self._get_ohlc_price_for_wick(peak_low_col, month_mapping, ohlc_data, 'low')
                
                if high_price is not None:
                    calibration_points.append({
                        "y": wick_high['y_px_abs'],
                        "price": high_price,
                        "source": "wick_high"
                    })
                
                if low_price is not None:
                    calibration_points.append({
                        "y": wick_low['y_px_abs'],
                        "price": low_price,
                        "source": "wick_low"
                    })
            
            # Calculate linear fit: price = α * y + β
            if len(calibration_points) >= 3:
                ys = np.array([p['y'] for p in calibration_points], dtype=float)
                ps = np.array([p['price'] for p in calibration_points], dtype=float)
                
                A = np.vstack([ys, np.ones_like(ys)]).T
                alpha, beta = np.linalg.lstsq(A, ps, rcond=None)[0]
                
                print(f"    ✅ Price formula: price = {alpha:.8f} * y + {beta:.8f}")
                
                # Calculate inverse formula for price -> y conversion
                # If price = alpha * y + beta, then y = (price - beta) / alpha
                inverse_alpha = 1.0 / alpha
                inverse_beta = -beta / alpha
                
                return {
                    "y_to_price": {
                        "alpha": float(alpha),
                        "beta": float(beta)
                    },
                    "price_to_y": {
                        "alpha": float(inverse_alpha),
                        "beta": float(inverse_beta)
                    },
                    "calibration_points": calibration_points
                }
            
            return None
            
        except Exception as e:
            print(f"    ❌ Price calibration failed: {e}")
            return None
    
    def _calculate_temporal_calibration(self, stage4c_results: Dict[str, Any], stage4ci_results: Dict[str, Any],
                                      stage4a_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate temporal calibration using actual OHLC high/low candles within month periods."""
        try:
            candle_map = stage4c_results
            month_mapping = stage4ci_results
            ohlc_data = stage4a_results.get('ohlc_data', {})
            
            if not month_mapping or 'peak_high_column' not in candle_map or 'peak_low_column' not in candle_map:
                print(f"    ⚠️ Missing data for temporal calibration")
                return None
            
            peak_high_col = candle_map['peak_high_column']
            peak_low_col = candle_map['peak_low_column']
            wick_high = candle_map['top_wicks'].get(peak_high_col)
            wick_low = candle_map['bottom_wicks'].get(peak_low_col)
            
            if not wick_high or not wick_low:
                print(f"    ⚠️ Missing wick data for temporal calibration")
                return None
            
            print(f"    🔍 Temporal calibration data:")
            print(f"      - Peak high: {peak_high_col} @ x={wick_high['x_px_abs']}")
            print(f"      - Peak low: {peak_low_col} @ x={wick_low['x_px_abs']}")
            
            # Extract month periods for each column
            high_month_period = month_mapping.get(peak_high_col, "")
            low_month_period = month_mapping.get(peak_low_col, "")
            
            print(f"      - {peak_high_col} period: {high_month_period}")
            print(f"      - {peak_low_col} period: {low_month_period}")
            
            # Find actual high/low candles within these periods
            temporal_points = []
            
            # Find highest candle in high month period
            if high_month_period and ohlc_data:
                high_candle = self._find_highest_candle_in_period(high_month_period, ohlc_data)
                if high_candle:
                    temporal_points.append({
                        "x": wick_high['x_px_abs'],
                        "timestamp": high_candle['timestamp'],
                        "date": high_candle['date'],
                        "price": high_candle['high'],
                        "source": "wick_high"
                    })
                    print(f"      ✅ Found highest candle in {high_month_period}: {high_candle['date']} @ {high_candle['high']:.4f}")
            
            # Find lowest candle in low month period  
            if low_month_period and ohlc_data:
                low_candle = self._find_lowest_candle_in_period(low_month_period, ohlc_data)
                if low_candle:
                    temporal_points.append({
                        "x": wick_low['x_px_abs'],
                        "timestamp": low_candle['timestamp'],
                        "date": low_candle['date'],
                        "price": low_candle['low'],
                        "source": "wick_low"
                    })
                    print(f"      ✅ Found lowest candle in {low_month_period}: {low_candle['date']} @ {low_candle['low']:.4f}")
            
            # Calculate temporal formula: timestamp = γ*x + δ
            if len(temporal_points) >= 2:
                x1, x2 = temporal_points[0]['x'], temporal_points[1]['x']
                timestamp1, timestamp2 = temporal_points[0]['timestamp'], temporal_points[1]['timestamp']
                
                # Calculate γ and δ
                gamma = (timestamp2 - timestamp1) / (x2 - x1)
                delta = timestamp1 - gamma * x1
                
                temporal_formula = {
                    "gamma": gamma,
                    "delta": delta,
                    "calibration_points": temporal_points
                }
                
                print(f"    ✅ Temporal formula: timestamp = {gamma:.8f} * x + {delta:.2f}")
                return temporal_formula
            else:
                print("    ⚠️ Insufficient temporal points for calibration")
                return None
            
        except Exception as e:
            print(f"    ❌ Temporal calibration failed: {e}")
            return None
    
    def _find_highest_candle_in_period(self, month_period: str, ohlc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the highest candle within a month period."""
        try:
            from datetime import datetime
            
            ohlcv = ohlc_data.get('ohlcv', [])
            if not ohlcv:
                return None
            
            # Parse month period (e.g., "May-Jun", "Apr-May")
            months = self._parse_month_period(month_period)
            if not months:
                return None
            
            highest_candle = None
            highest_price = 0
            
            for candle in ohlcv:
                timestamp = candle[0] / 1000  # Convert from milliseconds
                date = datetime.fromtimestamp(timestamp)
                
                # Check if candle is in the target month period
                if date.month in months:
                    high_price = candle[2]  # OHLC[2] is high
                    if high_price > highest_price:
                        highest_price = high_price
                        highest_candle = {
                            'timestamp': timestamp,
                            'date': date.strftime('%Y-%m-%d'),
                            'high': high_price,
                            'low': candle[3],
                            'open': candle[1],
                            'close': candle[4]
                        }
            
            return highest_candle
            
        except Exception as e:
            print(f"    ⚠️ Error finding highest candle: {e}")
            return None
    
    def _find_lowest_candle_in_period(self, month_period: str, ohlc_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find the lowest candle within a month period."""
        try:
            from datetime import datetime
            
            ohlcv = ohlc_data.get('ohlcv', [])
            if not ohlcv:
                return None
            
            # Parse month period (e.g., "May-Jun", "Apr-May")
            months = self._parse_month_period(month_period)
            if not months:
                return None
            
            lowest_candle = None
            lowest_price = float('inf')
            
            for candle in ohlcv:
                timestamp = candle[0] / 1000  # Convert from milliseconds
                date = datetime.fromtimestamp(timestamp)
                
                # Check if candle is in the target month period
                if date.month in months:
                    low_price = candle[3]  # OHLC[3] is low
                    if low_price < lowest_price:
                        lowest_price = low_price
                        lowest_candle = {
                            'timestamp': timestamp,
                            'date': date.strftime('%Y-%m-%d'),
                            'high': candle[2],
                            'low': low_price,
                            'open': candle[1],
                            'close': candle[4]
                        }
            
            return lowest_candle
            
        except Exception as e:
            print(f"    ⚠️ Error finding lowest candle: {e}")
            return None
    
    def _parse_month_period(self, month_period: str) -> List[int]:
        """Parse month period string to list of month numbers."""
        try:
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            months = []
            parts = month_period.split('-')
            
            for part in parts:
                part = part.strip()
                for month_name, month_num in month_map.items():
                    if month_name in part:
                        months.append(month_num)
                        break
            
            return months
            
        except Exception as e:
            print(f"    ⚠️ Error parsing month period '{month_period}': {e}")
            return []
    
    def _get_ohlc_price_for_wick(self, column: str, month_mapping: Dict[str, str], 
                                ohlc_data: Dict[str, Any], price_type: str) -> Optional[float]:
        """Get actual OHLC price for a wick column and month period."""
        try:
            month_period = month_mapping.get(column, "")
            if not month_period:
                return None
            
            ohlcv = ohlc_data.get('ohlcv', [])
            if not ohlcv:
                return None
            
            # Parse month period
            months = self._parse_month_period(month_period)
            if not months:
                return None
            
            # Find the extreme price in the month period
            from datetime import datetime
            
            if price_type == 'high':
                extreme_price = 0
                for candle in ohlcv:
                    timestamp = candle[0] / 1000
                    date = datetime.fromtimestamp(timestamp)
                    if date.month in months:
                        high_price = candle[2]  # OHLC[2] is high
                        if high_price > extreme_price:
                            extreme_price = high_price
            else:  # low
                extreme_price = float('inf')
                for candle in ohlcv:
                    timestamp = candle[0] / 1000
                    date = datetime.fromtimestamp(timestamp)
                    if date.month in months:
                        low_price = candle[3]  # OHLC[3] is low
                        if low_price < extreme_price:
                            extreme_price = low_price
            
            return extreme_price if extreme_price != float('inf') else None
            
        except Exception as e:
            print(f"    ⚠️ Error getting OHLC price for {column}: {e}")
            return None
