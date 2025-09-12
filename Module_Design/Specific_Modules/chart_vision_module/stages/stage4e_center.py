import cv2
import numpy as np
import json
import os
import sys
from typing import List, Dict, Tuple, Any, Optional

# Add current directory to path for imports
sys.path.append('.')
sys.path.append('pipeline')

from grid_mapping import GridMapper

class Stage4ECenterLine:
    """Stage 4E: Advanced Sonar using center-line scanning approach"""
    
    def __init__(self, image_path: str, stage2_results: Dict, stage4_results: Dict):
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        self.height, self.width = self.image.shape[:2]
        self.stage2_results = stage2_results
        self.stage4_results = stage4_results
        
        # Create debug directory
        os.makedirs('stage4e_debug', exist_ok=True)
    
    def run(self) -> Dict[str, Any]:
        """Run center-line scanning for precise element detection"""
        print("🎯 Starting Stage 4E Center-Line Scanning...")
        
        # Get candle exclusions (same as stage4e_clean.py)
        candle_exclusions = self._create_candle_exclusions()
        print(f"✅ Created candle exclusions for {len(candle_exclusions)} candles")
        
        # Scan center lines
        all_pixels = []
        
        # Get grid metadata
        grid_metadata = self.stage2_results.get('grid_metadata', {})
        padding = int(grid_metadata.get('cell_padding', 0))
        cell_w = float(grid_metadata.get('cell_width_px', 100))
        grid_rows = int(grid_metadata.get('grid_rows', 6))
        
        # Scan columns B to G with 4 positions per column (1/4, 1/2, 3/4, 4/4)
        for col_ord in range(ord('B'), ord('G') + 1):
            col_letter = chr(col_ord)
            print(f"\n  Column {col_letter}:")
            
            # Calculate column boundaries
            col_zero = ord(col_letter.upper()) - ord('A')
            x0 = int(round(padding + col_zero * cell_w))
            x1 = int(round(padding + (col_zero + 1) * cell_w))
            
            # Calculate 4 scan positions: 1/4, 1/2, 3/4, 4/4
            scan_positions = [
                int(round(x0 + 0.25 * (x1 - x0))),  # 1/4 position
                int(round(x0 + 0.5 * (x1 - x0))),   # 1/2 position (center)
                int(round(x0 + 0.75 * (x1 - x0))),  # 3/4 position
                int(round(x0 + 1.0 * (x1 - x0)))    # 4/4 position (right edge)
            ]
            
            column_pixels = []
            for i, scan_x in enumerate(scan_positions):
                position_name = ['1/4', '1/2', '3/4', '4/4'][i]
                print(f"    Position {position_name} (x={scan_x}):")
                
                # Find candles in this x-range
                candles_in_column = self._get_candles_in_x_range(scan_x, candle_exclusions)
                
                # Scan from bottom to top
                bottom_pixels = self._scan_center_line_bottom(scan_x, candles_in_column)
                print(f"      Bottom scan: Found {len(bottom_pixels)} pixels")
                
                # Scan from top to bottom  
                top_pixels = self._scan_center_line_top(scan_x, candles_in_column)
                print(f"      Top scan: Found {len(top_pixels)} pixels")
                
                # Add to column pixels
                column_pixels.extend(bottom_pixels + top_pixels)
            
            # Deduplicate column pixels
            column_pixels = list(set(column_pixels))
            print(f"    Total unique pixels: {len(column_pixels)}")
            
            all_pixels.extend(column_pixels)
        
        print(f"✅ Collected {len(all_pixels)} pixels from center-line scanning")
        
        # Create candle_data structure for diagonal detection
        candle_data = {'candles': candle_exclusions}
        
        # Identify elements (simple approach for now)
        elements = self._identify_elements(all_pixels, candle_data)
        print(f"✅ Identified {len(elements)} elements")
        
        # Save debug images
        self._save_debug_images(all_pixels, elements, candle_exclusions)
        
        return {
            'approach': 'center_line',
            'elements': elements,
            'total_pixels': len(all_pixels),
            'success': True
        }
    
    def _create_candle_exclusions(self) -> List[Dict]:
        """Create candle exclusion zones (copied from working stage4e_clean.py)"""
        try:
            # Load calibration data
            with open('stage4_calibration.json', 'r') as f:
                calibration = json.load(f)
            
            # Load OHLC data
            ohlc_data = self.stage4_results.get('stage4a_results', {}).get('ohlc_data', {})
            if not ohlc_data:
                print("⚠️ No OHLC data available")
                return []
            
            candles = ohlc_data.get('ohlcv', [])
            if not candles:
                print("⚠️ No candles in OHLC data")
                return []
            
            print(f"📊 Loaded {len(candles)} candles from OHLC data")
            
            # Get calibration points
            price_calibration = calibration.get('price_calibration', {})
            temporal_calibration = calibration.get('temporal_calibration', {})
            
            if not price_calibration or not temporal_calibration:
                print("⚠️ Missing calibration data")
                return []
            
            # Get calibration points for linear interpolation (working approach)
            cal_points = temporal_calibration.get('calibration_points', [])
            if len(cal_points) < 2:
                print("⚠️ Need at least 2 calibration points for temporal mapping")
                return []
            
            point1 = cal_points[0]  # First calibration point
            point2 = cal_points[1]  # Second calibration point
            
            x1, t1 = point1['x'], point1['timestamp']
            x2, t2 = point2['x'], point2['timestamp']
            
            print(f"📊 Calibration points: ({x1}, {t1}) -> ({x2}, {t2})")
            
            # Simple linear interpolation function
            def timestamp_to_x(timestamp):
                return x1 + (timestamp - t1) * (x2 - x1) / (t2 - t1)
            
            # Get price calibration (price -> y conversion)
            price_to_y = price_calibration.get('price_to_y', {})
            if not price_to_y:
                print("⚠️ Missing price_to_y calibration")
                return []
            
            alpha = price_to_y.get('alpha', 0)
            beta = price_to_y.get('beta', 0)
            
            print(f"📊 Price calibration: alpha={alpha}, beta={beta}")
            
            candle_exclusions = []
            
            for i, candle in enumerate(candles):  # Process all candles
                timestamp = candle[0] / 1000.0  # Convert to seconds
                high_price = candle[2]
                low_price = candle[3]
                
                # Get coordinates using interpolation
                x = timestamp_to_x(timestamp)
                y_high = alpha * high_price + beta
                y_low = alpha * low_price + beta
                
                if i < 3:  # Debug first 3
                    print(f"    Candle {i}: x={x:.1f}, y_high={y_high:.1f}, y_low={y_low:.1f}")
                
                # Add margin for candle body
                margin = 5
                candle_exclusions.append({
                    'x': int(x),
                    'y_high': max(0, int(y_high - margin)),
                    'y_low': min(self.height - 1, int(y_low + margin)),
                    'high_price': high_price,
                    'low_price': low_price
                })
            
            return candle_exclusions
            
        except Exception as e:
            print(f"❌ Error creating candle exclusions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_candles_in_x_range(self, center_x: int, candle_exclusions: List[Dict]) -> List[Dict]:
        """Get candles that are in the x-range of this column (simple approach)"""
        # Use a 20-pixel range around center
        x_range = 20
        x_min = center_x - x_range
        x_max = center_x + x_range
        
        candles_in_range = []
        for candle in candle_exclusions:
            if x_min <= candle['x'] <= x_max:
                candles_in_range.append(candle)
        
        return candles_in_range
    
    def _scan_center_line_bottom(self, center_x: int, candles_in_column: List[Dict]) -> List[Tuple[int, int]]:
        """Scan center line from bottom to top, stopping at candle low"""
        detected_pixels = []
        
        # Find the lowest candle low in this column
        candle_low = None
        for candle in candles_in_column:
            if candle_low is None or candle['y_low'] > candle_low:
                candle_low = candle['y_low']
        
        # If no candles, scan entire column (respecting 150px skip)
        if candle_low is None:
            candle_low = 0  # Start from very bottom, but we'll respect 150px skip in crop
            print(f"    No candles found - scanning entire column from bottom")
        else:
            print(f"    Scanning from bottom to y={candle_low + 1} (candle low + 1)")
        
        # Create 10-pixel wide crop around center line
        crop_width = 10
        x0 = max(0, center_x - crop_width // 2)
        x1 = min(self.width, center_x + crop_width // 2)
        
        # Create crop for the scanning region (from bottom to candle low + 1, but skip bottom 150px)
        if candle_low == 0:
            # No candles: scan entire column with 150px skip
            y0 = 150  # Skip top 150px
            y1 = self.height - 150  # Skip bottom 150px
        else:
            # Has candles: scan from candle low + 1 to bottom with 150px skip
            y0 = candle_low + 1
            y1 = self.height - 150  # Skip bottom 150px
        crop = self.image[y0:y1, x0:x1]
        
        if crop.size == 0:
            return detected_pixels
        
        # Apply Canny to the entire crop
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Find all edge pixels
        ys, xs = np.where(edges == 255)
        if ys.size == 0:
            return detected_pixels
        
        # Convert to absolute coordinates and add to detected pixels
        for i in range(len(ys)):
            y_abs = int(y0 + ys[i])
            x_abs = int(x0 + xs[i])
            detected_pixels.append((x_abs, y_abs))
            print(f"    Found edge pixel at ({x_abs}, {y_abs})")
        
        return detected_pixels
    
    def _scan_center_line_top(self, center_x: int, candles_in_column: List[Dict]) -> List[Tuple[int, int]]:
        """Scan center line from top to bottom, stopping at candle high"""
        detected_pixels = []
        
        # Find the highest candle high in this column
        candle_high = None
        for candle in candles_in_column:
            if candle_high is None or candle['y_high'] < candle_high:
                candle_high = candle['y_high']
        
        # If no candles, scan entire column (respecting 150px skip)
        if candle_high is None:
            candle_high = self.height  # Go to very bottom, but we'll respect 150px skip in crop
            print(f"    No candles found - scanning entire column from top")
        else:
            print(f"    Scanning from top to y={candle_high - 1} (candle high - 1)")
        
        # Create 10-pixel wide crop around center line
        crop_width = 10
        x0 = max(0, center_x - crop_width // 2)
        x1 = min(self.width, center_x + crop_width // 2)
        
        # Create crop for the scanning region (from top to candle high - 1, but skip top 150px)
        if candle_high == self.height:
            # No candles: scan entire column with 150px skip
            y0 = 150  # Skip top 150px
            y1 = self.height - 150  # Skip bottom 150px
        else:
            # Has candles: scan from top with 150px skip to candle high - 1
            y0 = 150  # Skip top 150px
            y1 = candle_high
        crop = self.image[y0:y1, x0:x1]
        
        if crop.size == 0:
            return detected_pixels
        
        # Apply Canny to the entire crop
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Find all edge pixels
        ys, xs = np.where(edges == 255)
        if ys.size == 0:
            return detected_pixels
        
        # Convert to absolute coordinates and add to detected pixels
        for i in range(len(ys)):
            y_abs = int(y0 + ys[i])
            x_abs = int(x0 + xs[i])
            detected_pixels.append((x_abs, y_abs))
            print(f"    Found edge pixel at ({x_abs}, {y_abs})")
        
        return detected_pixels
    
    def _is_candle_pixel(self, x: int, y: int, candles_in_column: List[Dict]) -> bool:
        """Check if pixel is within a candle exclusion zone"""
        for candle in candles_in_column:
            if (abs(x - candle['x']) <= 5 and 
                candle['y_low'] <= y <= candle['y_high']):
                return True
        return False
    
    def _identify_elements(self, pixels: List[Tuple[int, int]], candle_data: Dict) -> List[Dict]:
        """Element identification with horizontal line detection"""
        elements = []
        
        # Get grid metadata for proper column mapping
        grid_metadata = self.stage2_results.get('grid_metadata', {})
        padding = int(grid_metadata.get('cell_padding', 0))
        cell_w = float(grid_metadata.get('cell_width_px', 100))
        
        # Load Stage 2Di results for known horizontal lines
        stage2di_results = self.stage2_results.get('stage2di_results', [])
        known_horizontal_lines = []
        for line in stage2di_results:
            known_horizontal_lines.append({
                'element_id': line.get('element_id'),
                'y_pixel': line.get('coordinates', {}).get('y_pixel'),
                'confidence': line.get('coordinates', {}).get('confidence', 0.9)
            })
        
        print(f"🔍 Looking for {len(known_horizontal_lines)} known horizontal lines")
        
        # Load Stage 2Diii results for known zones
        stage2diii_results = self.stage2_results.get('stage2diii_results', [])
        known_zones = []
        for zone in stage2diii_results:
            known_zones.append({
                'element_id': zone.get('element_id'),
                'y_top_px': zone.get('y_top_px'),
                'y_bottom_px': zone.get('y_bottom_px'),
                'area': zone.get('area')
            })
        
        print(f"🔍 Looking for {len(known_zones)} known zones")
        
        # Group pixels by actual column (B-G)
        columns = {}
        for x, y in pixels:
            # Calculate which column this x-coordinate belongs to
            col_zero = int((x - padding) // cell_w)
            if 1 <= col_zero <= 6:  # Columns B-G (1-6 in zero-based)
                col_letter = chr(ord('A') + col_zero)
                if col_letter not in columns:
                    columns[col_letter] = []
                columns[col_letter].append((x, y))
        
        # First, try to identify horizontal lines
        for known_line in known_horizontal_lines:
            if known_line['y_pixel'] is None:
                continue
                
            target_y = known_line['y_pixel']
            tolerance = 2  # ±2px tolerance
            
            # Find pixels within tolerance of the known horizontal line
            horizontal_pixels = []
            for col_letter, col_pixels in columns.items():
                for x, y in col_pixels:
                    if abs(y - target_y) <= tolerance:
                        horizontal_pixels.append((x, y))
            
            if len(horizontal_pixels) >= 20:  # Minimum pixels for a horizontal line
                # Calculate actual y-coordinate from detected pixels
                detected_ys = [y for x, y in horizontal_pixels]
                actual_y = int(sum(detected_ys) / len(detected_ys))  # Average y
                
                # Get columns where this horizontal line was detected
                detected_columns = set()
                for x, y in horizontal_pixels:
                    col_zero = int((x - padding) // cell_w)
                    if 1 <= col_zero <= 6:
                        col_letter = chr(ord('A') + col_zero)
                        detected_columns.add(col_letter)
                
                elements.append({
                    'type': 'horizontal_line',
                    'element_id': known_line['element_id'],
                    'pixels': len(horizontal_pixels),
                    'columns': sorted(list(detected_columns)),
                    'y_detected': actual_y,
                    'y_expected': target_y,
                    'y_offset': actual_y - target_y,
                    'confidence': known_line['confidence']
                })
                
                print(f"✅ Found horizontal line {known_line['element_id']}: y={actual_y} (expected {target_y}, offset {actual_y - target_y})")
                
                # Remove these pixels from further processing
                for x, y in horizontal_pixels:
                    col_zero = int((x - padding) // cell_w)
                    if 1 <= col_zero <= 6:
                        col_letter = chr(ord('A') + col_zero)
                        if (x, y) in columns[col_letter]:
                            columns[col_letter].remove((x, y))
        
        # Second, try to identify zones
        for known_zone in known_zones:
            if known_zone['y_top_px'] is None or known_zone['y_bottom_px'] is None:
                continue
                
            target_y_top = known_zone['y_top_px']
            target_y_bottom = known_zone['y_bottom_px']
            tolerance = 6  # ±6px tolerance for zones
            
            # Find pixels that are actually on the zone boundaries (the lines), not in the space between
            zone_pixels = []
            for col_letter, col_pixels in columns.items():
                for x, y in col_pixels:
                    # Only collect pixels that are near the top or bottom boundary lines
                    # Top boundary: within tolerance of target_y_top
                    # Bottom boundary: within tolerance of target_y_bottom
                    if (abs(y - target_y_top) <= tolerance or abs(y - target_y_bottom) <= tolerance):
                        zone_pixels.append((x, y))
            
            # If we found pixels, extend the search to include nearby pixels that might be part of the same boundary lines
            if len(zone_pixels) >= 10:  # If we found a reasonable number of pixels
                # Calculate actual detected boundaries
                detected_ys = [y for x, y in zone_pixels]
                actual_y_top = min(detected_ys)
                actual_y_bottom = max(detected_ys)
                
                # Look for additional pixels within 5px of the actual detected boundary lines only
                extended_zone_pixels = []
                for col_letter, col_pixels in columns.items():
                    for x, y in col_pixels:
                        # Only include pixels near the actual detected boundary lines
                        if (abs(y - actual_y_top) <= 5 or abs(y - actual_y_bottom) <= 5):
                            extended_zone_pixels.append((x, y))
                
                # Use the extended pixel set if it's reasonable
                if len(extended_zone_pixels) > len(zone_pixels):
                    zone_pixels = extended_zone_pixels
            
            # Validate zone boundaries before proceeding
            if len(zone_pixels) >= 15 and self._validate_zone_boundaries(zone_pixels, target_y_top, target_y_bottom, tolerance):
                # Calculate actual zone boundaries from detected pixels
                detected_ys = [y for x, y in zone_pixels]
                
                # Separate top and bottom boundary lines
                # Top boundary: pixels within tolerance of target_y_top
                top_boundary_ys = [y for x, y in zone_pixels if abs(y - target_y_top) <= tolerance]
                # Bottom boundary: pixels within tolerance of target_y_bottom  
                bottom_boundary_ys = [y for x, y in zone_pixels if abs(y - target_y_bottom) <= tolerance]
                
                # Calculate actual boundary line ranges
                actual_y_top_min = min(top_boundary_ys) if top_boundary_ys else min(detected_ys)
                actual_y_top_max = max(top_boundary_ys) if top_boundary_ys else min(detected_ys)
                actual_y_bottom_min = min(bottom_boundary_ys) if bottom_boundary_ys else max(detected_ys)
                actual_y_bottom_max = max(bottom_boundary_ys) if bottom_boundary_ys else max(detected_ys)
                
                # For display purposes, show the full range but note the boundary lines
                actual_y_top = min(detected_ys)
                actual_y_bottom = max(detected_ys)
                
                # Get columns where this zone was detected
                detected_columns = set()
                for x, y in zone_pixels:
                    col_zero = int((x - padding) // cell_w)
                    if 1 <= col_zero <= 6:
                        col_letter = chr(ord('A') + col_zero)
                        detected_columns.add(col_letter)
                
                # Calculate x-range of the zone
                detected_xs = [x for x, y in zone_pixels]
                actual_x_min = min(detected_xs)
                actual_x_max = max(detected_xs)
                
                elements.append({
                    'type': 'zone',
                    'element_id': known_zone['element_id'],
                    'pixels': len(zone_pixels),
                    'columns': sorted(list(detected_columns)),
                    'y_top_detected': actual_y_top,
                    'y_bottom_detected': actual_y_bottom,
                    'y_top_expected': target_y_top,
                    'y_bottom_expected': target_y_bottom,
                    'y_top_offset': actual_y_top - target_y_top,
                    'y_bottom_offset': actual_y_bottom - target_y_bottom,
                    'x_range': [actual_x_min, actual_x_max],
                    'area_expected': known_zone['area'],
                    'top_boundary_range': [actual_y_top_min, actual_y_top_max],
                    'bottom_boundary_range': [actual_y_bottom_min, actual_y_bottom_max]
                })
                
                print(f"✅ Found zone {known_zone['element_id']}: y={actual_y_top}-{actual_y_bottom} (expected {target_y_top}-{target_y_bottom})")
                
                # Remove these pixels from further processing
                for x, y in zone_pixels:
                    col_zero = int((x - padding) // cell_w)
                    if 1 <= col_zero <= 6:
                        col_letter = chr(ord('A') + col_zero)
                        if (x, y) in columns[col_letter]:
                            columns[col_letter].remove((x, y))
        
        # Third, try to identify diagonal lines from remaining pixels
        diagonal_elements = self._detect_diagonal_lines(columns, grid_metadata, candle_data)
        elements.extend(diagonal_elements)
        
        # Remove diagonal pixels from further processing
        for diagonal in diagonal_elements:
            diagonal_pixels = diagonal.get('pixels_list', [])
            for x, y in diagonal_pixels:
                col_zero = int((x - padding) // cell_w)
                if 1 <= col_zero <= 6:
                    col_letter = chr(ord('A') + col_zero)
                    if (x, y) in columns[col_letter]:
                        columns[col_letter].remove((x, y))
        
        # Create simple elements for remaining pixels
        for col_letter, col_pixels in columns.items():
            if len(col_pixels) > 10:  # Minimum pixels for an element
                ys = [y for x, y in col_pixels]
                elements.append({
                    'type': 'unknown',
                    'pixels': len(col_pixels),
                    'column': col_letter,
                    'y_range': [min(ys), max(ys)]
                })
        
        return elements
    
    def _validate_zone_boundaries(self, zone_pixels: List[Tuple[int, int]], target_y_top: int, target_y_bottom: int, tolerance: int) -> bool:
        """
        Validate that zone pixels form proper horizontal boundaries.
        
        Requirements:
        1. At least 3 different X-positions at top boundary (within tolerance of target_y_top)
        2. At least 3 different X-positions at bottom boundary (within tolerance of target_y_bottom)
        3. X-positions must be meaningfully spread out (at least 20px apart)
        """
        # Group pixels by Y-coordinate
        y_groups = {}
        for x, y in zone_pixels:
            if y not in y_groups:
                y_groups[y] = []
            y_groups[y].append(x)
        
        # Find top boundary pixels (within tolerance of target_y_top)
        top_boundary_pixels = []
        for y in y_groups:
            if abs(y - target_y_top) <= tolerance:
                top_boundary_pixels.extend(y_groups[y])
        
        # Find bottom boundary pixels (within tolerance of target_y_bottom)
        bottom_boundary_pixels = []
        for y in y_groups:
            if abs(y - target_y_bottom) <= tolerance:
                bottom_boundary_pixels.extend(y_groups[y])
        
        # Check if we have enough pixels at each boundary
        if len(top_boundary_pixels) < 3 or len(bottom_boundary_pixels) < 3:
            return False
        
        # Check horizontal spread at top boundary
        top_x_positions = sorted(set(top_boundary_pixels))
        if len(top_x_positions) < 3:
            return False
        
        # Check if top X-positions are meaningfully spread out (at least 20px apart)
        top_spread = max(top_x_positions) - min(top_x_positions)
        if top_spread < 20:
            return False
        
        # Check horizontal spread at bottom boundary
        bottom_x_positions = sorted(set(bottom_boundary_pixels))
        if len(bottom_x_positions) < 3:
            return False
        
        # Check if bottom X-positions are meaningfully spread out (at least 20px apart)
        bottom_spread = max(bottom_x_positions) - min(bottom_x_positions)
        if bottom_spread < 20:
            return False
        
        return True
    
    def _detect_diagonal_lines(self, columns: Dict[str, List[Tuple[int, int]]], grid_metadata: Dict, candle_data: Dict) -> List[Dict]:
        """
        Detect diagonal lines by analyzing clusters within each 10px scan area.
        
        Strategy:
        1. Group pixels by scan position (10px wide areas)
        2. Within each scan, separate pixels into clusters by Y-coordinate proximity
        3. Compare cluster Y-coords to candle Y-coords in the same scan range
        4. Classify as above/below candles and map to appropriate element IDs
        5. Validate pixels are within Stage 2B diagonal areas
        """
        diagonals = []
        padding = int(grid_metadata.get('cell_padding', 0))
        cell_w = float(grid_metadata.get('cell_width_px', 100))
        cell_h = float(grid_metadata.get('cell_height_px', 100))
        grid_rows = int(grid_metadata.get('grid_rows', 6))
        
        # Load Stage 2B diagonal areas for validation
        stage2b_areas = self._load_stage2b_diagonal_areas(grid_metadata)
        
        # Group pixels by scan position (10px wide areas)
        scan_groups = {}
        for col_letter, col_pixels in columns.items():
            for x, y in col_pixels:
                # Round x to nearest scan position (every ~67px for 4 positions per column)
                scan_x = round(x / 67) * 67
                if scan_x not in scan_groups:
                    scan_groups[scan_x] = []
                scan_groups[scan_x].append((x, y))
        
        # Analyze each scan group
        for scan_x, pixels in scan_groups.items():
            if len(pixels) < 2:  # Need at least 2 pixels
                continue
            
            # Get candle Y-coordinates for this scan range
            candle_ys = self._get_candle_ys_for_scan(scan_x, candle_data)
            if not candle_ys:
                continue  # Skip if no candles in this scan range
            
            # Separate pixels into clusters by Y-coordinate proximity
            clusters = self._cluster_pixels_by_y(pixels)
            
            # Analyze each cluster for diagonal patterns
            for cluster in clusters:
                if len(cluster) < 2:  # Need at least 2 pixels in cluster
                    continue
                
                # Get Y-coordinates and check for diagonal pattern
                ys = [y for x, y in cluster]
                xs = [x for x, y in cluster]
                y_min, y_max = min(ys), max(ys)
                x_min, x_max = min(xs), max(xs)
                y_range = y_max - y_min
                x_range = x_max - x_min
                
                # Simple rule: if Y-range > 2px AND X-range > 2px AND pixel count <= 20, it's a diagonal
                if y_range > 2 and x_range > 2 and len(cluster) <= 20:  # Both Y and X ranges > 2px, max 20 pixels
                    # Validate that cluster pixels are within Stage 2B diagonal areas
                    if not self._validate_cluster_in_stage2b_area(cluster, stage2b_areas):
                        continue
                    
                    # Determine if cluster is above or below candles
                    cluster_avg_y = sum(ys) / len(ys)
                    candle_avg_y = sum(candle_ys) / len(candle_ys)
                    
                    if cluster_avg_y < candle_avg_y:
                        position = "above"
                    else:
                        position = "below"
                    
                    # Map to element ID based on position (dynamic)
                    element_id = self._map_position_to_element_id(position, grid_metadata)
                    
                    diagonals.append({
                        'type': 'diagonal_line',
                        'element_id': element_id,
                        'position': position,
                        'pixels': len(cluster),
                        'pixels_list': cluster,
                        'y_range': y_range,
                        'scan_x': scan_x,
                        'y_min': y_min,
                        'y_max': y_max,
                        'cluster_avg_y': cluster_avg_y,
                        'candle_avg_y': candle_avg_y
                    })
                    
                    print(f"✅ Found diagonal {element_id} ({position} candles): y_range={y_range}, x_range={x_range}, {len(cluster)} pixels at x={scan_x}")
        
        return diagonals
    
    def _cluster_pixels_by_y(self, pixels: List[Tuple[int, int]], max_gap: int = 3) -> List[List[Tuple[int, int]]]:
        """
        Separate pixels into clusters based on Y-coordinate proximity.
        Pixels within max_gap pixels of each other in Y are grouped together.
        """
        if not pixels:
            return []
        
        # Sort pixels by Y-coordinate
        sorted_pixels = sorted(pixels, key=lambda p: p[1])
        
        clusters = []
        current_cluster = [sorted_pixels[0]]
        
        for i in range(1, len(sorted_pixels)):
            current_y = sorted_pixels[i][1]
            prev_y = sorted_pixels[i-1][1]
            
            if current_y - prev_y <= max_gap:
                # Add to current cluster
                current_cluster.append(sorted_pixels[i])
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [sorted_pixels[i]]
        
        # Add the last cluster
        clusters.append(current_cluster)
        
        return clusters
    
    def _get_candle_ys_for_scan(self, scan_x: int, candle_data: Dict) -> List[int]:
        """
        Get candle Y-coordinates for a specific scan range.
        """
        candle_ys = []
        
        # Find candles that fall within this scan range (10px wide)
        for candle in candle_data.get('candles', []):
            candle_x = candle.get('x', 0)
            # Check if candle is within 5px of the scan center
            if abs(candle_x - scan_x) <= 5:
                # Use y_high and y_low to get the candle's Y range
                y_high = candle.get('y_high', 0)
                y_low = candle.get('y_low', 0)
                # Use the middle of the candle as the reference point
                candle_center_y = (y_high + y_low) / 2
                candle_ys.append(candle_center_y)
        
        return candle_ys
    
    def _map_position_to_element_id(self, position: str, grid_metadata: Dict) -> str:
        """
        Map position (above/below) to appropriate element ID dynamically.
        """
        # For now, use simple mapping - can be enhanced based on Stage 2 results
        if position == "above":
            return "ELEMENT_04"  # Top diagonal
        else:
            return "ELEMENT_05"  # Bottom diagonal
    
    def _classify_diagonal_direction(self, cluster: List[Tuple[int, int]]) -> str:
        """
        Classify diagonal direction based on slope.
        """
        if len(cluster) < 2:
            return 'ELEMENT_DIAGONAL'
        
        # Sort by X-coordinate
        sorted_cluster = sorted(cluster, key=lambda p: p[0])
        
        # Calculate slope
        x1, y1 = sorted_cluster[0]
        x2, y2 = sorted_cluster[-1]
        
        if x2 != x1:
            slope = (y2 - y1) / (x2 - x1)
            if slope < -0.5:
                return 'ELEMENT_04'  # Negative slope (resistance)
            elif slope > 0.5:
                return 'ELEMENT_05'  # Positive slope (support)
        
        return 'ELEMENT_DIAGONAL'
    
    def _deduplicate_diagonals(self, diagonals: List[Dict]) -> List[Dict]:
        """
        Deduplicate similar diagonal detections by grouping lines with similar slopes
        and overlapping coordinates, keeping the best detection from each group.
        """
        if len(diagonals) <= 1:
            return diagonals
        
        # Group diagonals by similarity
        groups = []
        used_indices = set()
        
        for i, diag1 in enumerate(diagonals):
            if i in used_indices:
                continue
                
            # Start a new group with this diagonal
            group = [i]
            used_indices.add(i)
            slope1 = diag1['slope']
            pixels1 = set(diag1['pixels_list'])
            
            # Find similar diagonals
            for j, diag2 in enumerate(diagonals[i+1:], i+1):
                if j in used_indices:
                    continue
                    
                slope2 = diag2['slope']
                pixels2 = set(diag2['pixels_list'])
                
                # Check if slopes are similar (within 0.2 for more aggressive grouping)
                slope_diff = abs(slope1 - slope2)
                
                # Check if pixels overlap significantly (at least 30% overlap)
                overlap = len(pixels1.intersection(pixels2))
                min_pixels = min(len(pixels1), len(pixels2))
                overlap_ratio = overlap / min_pixels if min_pixels > 0 else 0
                
                # Group if slopes are similar AND pixels overlap significantly
                if slope_diff < 0.2 and overlap_ratio > 0.3:
                    group.append(j)
                    used_indices.add(j)
            
            groups.append(group)
        
        # Keep the best diagonal from each group
        deduplicated = []
        for group in groups:
            if not group:
                continue
                
            # Find the diagonal with the most pixels in this group
            best_diag = max([diagonals[i] for i in group], key=lambda d: len(d['pixels_list']))
            
            # Update element_id based on slope
            if abs(best_diag['slope']) < 0.1:
                best_diag['element_id'] = 'ELEMENT_HORIZONTAL'
            elif best_diag['slope'] < -0.5:
                best_diag['element_id'] = 'ELEMENT_04'  # Negative slope (resistance)
            elif best_diag['slope'] > 0.5:
                best_diag['element_id'] = 'ELEMENT_05'  # Positive slope (support)
            else:
                best_diag['element_id'] = 'ELEMENT_DIAGONAL'
            
            deduplicated.append(best_diag)
            print(f"✅ Deduplicated diagonal group: {best_diag['element_id']} slope={best_diag['slope']:.3f}, {len(best_diag['pixels_list'])} pixels")
        
        return deduplicated
    
    def _validate_diagonal_area(self, diagonal_pixels: List[Tuple[int, int]], grid_metadata: Dict) -> Optional[Dict]:
        """
        Check if diagonal pixels are in rough known diagonal areas from Stage 2B.
        """
        padding = int(grid_metadata.get('cell_padding', 0))
        cell_w = float(grid_metadata.get('cell_width_px', 100))
        cell_h = float(grid_metadata.get('cell_height_px', 170))
        
        # Get pixel bounds
        xs = [x for x, y in diagonal_pixels]
        ys = [y for x, y in diagonal_pixels]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Convert to grid coordinates
        min_col = int((min_x - padding) // cell_w)
        max_col = int((max_x - padding) // cell_w)
        min_row = int((min_y - padding) // cell_h)
        max_row = int((max_y - padding) // cell_h)
        
        # Check against known diagonal areas from Stage 2B
        known_diagonals = [
            {'element_id': 'ELEMENT_04', 'area': 'C5→F3', 'cols': [2, 5], 'rows': [4, 2]},  # C5 to F3
            {'element_id': 'ELEMENT_05', 'area': 'C3→F1', 'cols': [2, 5], 'rows': [2, 0]}   # C3 to F1
        ]
        
        for known in known_diagonals:
            # Check if our diagonal overlaps with known area
            if (min_col <= known['cols'][1] and max_col >= known['cols'][0] and
                min_row <= known['rows'][1] and max_row >= known['rows'][0]):
                return {
                    'element_id': known['element_id'],
                    'area': known['area'],
                    'confidence': 0.8
                }
        
        return None
    
    def _load_stage2b_diagonal_areas(self, grid_metadata: Dict) -> Dict[str, Dict]:
        """
        Load Stage 2B diagonal areas and convert to pixel rectangles.
        Returns dict mapping element_id to rectangle boundaries.
        """
        stage2b_results = self.stage2_results.get('stage2b_results', {})
        diagonal_lines = stage2b_results.get('diagonal_lines', [])
        
        # Create GridMapper instance for proper coordinate conversion
        grid_mapper = GridMapper(grid_metadata['grid_cols'], grid_metadata['grid_rows'])
        
        areas = {}
        
        for diagonal in diagonal_lines:
            element_id = diagonal.get('element_id')
            start_cell = diagonal.get('start')  # e.g., "C5"
            end_cell = diagonal.get('end')      # e.g., "F3"
            
            if not element_id or not start_cell or not end_cell:
                continue
            
            # Parse grid coordinates
            start_col = start_cell[0]  # e.g., "C"
            start_row = int(start_cell[1])  # e.g., 5
            end_col = end_cell[0]  # e.g., "F"
            end_row = int(end_cell[1])  # e.g., 3
            
            # Use GridMapper to get proper rectangle coordinates
            # C5 (top-left corner)
            c5_x, c5_y = grid_mapper.cell_to_pixel(start_col, start_row, grid_metadata, u=0.0, v=1.0)
            # F5 (top-right corner)
            f5_x, f5_y = grid_mapper.cell_to_pixel(end_col, start_row, grid_metadata, u=1.0, v=1.0)
            # F3 (bottom-right corner)
            f3_x, f3_y = grid_mapper.cell_to_pixel(end_col, end_row, grid_metadata, u=1.0, v=0.0)
            # C3 (bottom-left corner)
            c3_x, c3_y = grid_mapper.cell_to_pixel(start_col, end_row, grid_metadata, u=0.0, v=0.0)
            
            # Calculate rectangle bounds
            x1 = min(c5_x, f5_x, f3_x, c3_x)
            x2 = max(c5_x, f5_x, f3_x, c3_x)
            y1 = min(c5_y, f5_y, f3_y, c3_y)
            y2 = max(c5_y, f5_y, f3_y, c3_y)
            
            areas[element_id] = {
                'x_min': x1,
                'x_max': x2,
                'y_min': y1,
                'y_max': y2,
                'start_cell': start_cell,
                'end_cell': end_cell
            }
            
            print(f"    Stage 2B area for {element_id}: {start_cell}→{end_cell} = pixels ({x1},{y1}) to ({x2},{y2})")
        
        return areas
    
    def _validate_cluster_in_stage2b_area(self, cluster: List[Tuple[int, int]], stage2b_areas: Dict[str, Dict]) -> bool:
        """
        Validate that cluster pixels are within ANY Stage 2B diagonal area.
        Returns True if at least 50% of pixels are within any Stage 2B diagonal area.
        """
        if not stage2b_areas:
            return True  # No areas to validate against
        
        pixels_in_any_area = 0
        total_pixels = len(cluster)
        
        for x, y in cluster:
            # Check if pixel is in ANY Stage 2B diagonal area
            for element_id, area in stage2b_areas.items():
                if (area['x_min'] <= x <= area['x_max'] and 
                    area['y_min'] <= y <= area['y_max']):
                    pixels_in_any_area += 1
                    break  # Pixel is in at least one area, no need to check others
        
        # Require at least 50% of pixels to be in ANY diagonal area
        return (pixels_in_any_area / total_pixels) >= 0.5
    
    def _save_debug_images(self, pixels: List[Tuple[int, int]], elements: List[Dict], candle_exclusions: List[Dict]):
        """Save debug images"""
        # Create pixel overlay
        debug_img = self.image.copy()
        
        # Draw detected pixels
        for x, y in pixels:
            cv2.circle(debug_img, (x, y), 1, (0, 255, 0), -1)
        
        # Draw diagonal lines in red
        for element in elements:
            if element['type'] == 'diagonal_line':
                diagonal_pixels = element.get('pixels_list', [])
                # Color all diagonal pixels red
                color = (0, 0, 255)  # Red for all diagonals
                
                for x, y in diagonal_pixels:
                    cv2.circle(debug_img, (x, y), 2, color, -1)
        
        # Draw candle exclusions
        for candle in candle_exclusions:
            x = int(candle['x'])
            y_high = int(candle['y_high'])
            y_low = int(candle['y_low'])
            cv2.rectangle(debug_img, 
                         (x - 5, y_high), 
                         (x + 5, y_low), 
                         (0, 0, 255), 1)
        
        cv2.imwrite('stage4e_debug/center_line_pixels.png', debug_img)
        print("🖼️ Debug Images:")
        print("   - stage4e_debug/center_line_pixels.png (center-line pixels)")


if __name__ == "__main__":
    # Test the center-line scanning
    import sys
    sys.path.append('.')
    
    # Load test data
    with open('stage2_results.json', 'r') as f:
        stage2_results = json.load(f)
    
    with open('stage4_results.json', 'r') as f:
        stage4_results = json.load(f)
    
    # Run center-line scanning
    detector = Stage4ECenterLine('kaito_image.png', stage2_results, stage4_results)
    results = detector.run()
    
    # Save results
    with open('stage4e_center_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("✅ Results saved to stage4e_center_results.json")
    
    # Print summary
    print(f"\n📊 Stage 4E Center-Line Results Summary:")
    print("=" * 50)
    print(f"🎯 Approach: {results['approach']}")
    print(f"📊 Total Elements: {len(results['elements'])}")
    print(f"📊 Total Pixels: {results['total_pixels']}")
    print(f"✅ Success: {results['success']}")
    
    for i, element in enumerate(results['elements'], 1):
        element_name = element.get('element_id', f'unknown_{i}')
        print(f"  {element_name}: {element['type']} - {element['pixels']} pixels")
        if 'column' in element:
            print(f"    Column: {element['column']}")
        if 'y_range' in element:
            print(f"    Y Range: {element['y_range']}")
        if element['type'] == 'zone':
            print(f"    Y Boundaries: {element.get('y_top_detected', 'N/A')}-{element.get('y_bottom_detected', 'N/A')} (expected {element.get('y_top_expected', 'N/A')}-{element.get('y_bottom_expected', 'N/A')})")
            if 'top_boundary_range' in element and 'bottom_boundary_range' in element:
                top_range = element['top_boundary_range']
                bottom_range = element['bottom_boundary_range']
                print(f"    Top boundary line: Y={top_range[0]}-{top_range[1]} (excluded)")
                print(f"    Bottom boundary line: Y={bottom_range[0]}-{bottom_range[1]} (excluded)")
                print(f"    Available space: Y={top_range[1]+1}-{bottom_range[0]-1} (available for other elements)")
            print(f"    Columns: {element.get('columns', [])}")
    
    print("🎉 Stage 4E Center-Line test completed!")
