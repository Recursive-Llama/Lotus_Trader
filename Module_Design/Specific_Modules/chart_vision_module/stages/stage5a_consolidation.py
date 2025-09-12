#!/usr/bin/env python3
"""
Stage 5A: Data Consolidation & Analysis

Consolidates data from all pipeline stages into a unified structure for:
1. Chart rebuilding (Stage 5B)
2. LLM decision maker

Priority Logic:
- Stage 4E data = Primary (pixel-perfect)
- Stage 2 data = Fallback (grid-based)
- No arrows (already converted to trader intent)
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add pipeline directory to path for GridMapper import
sys.path.append('pipeline')
from grid_mapping import GridMapper

class Stage5AConsolidation:
    def __init__(self, image_path: str = "kaito_image_grid.png"):
        self.image_path = image_path
        self.stage2_results = {}
        self.stage4e_results = {}
        self.stage3_results = {}
        self.stage4d_results = {}
        self.ohlc_data = {}
        
    def load_all_data(self):
        """Load data from all pipeline stages"""
        print("📊 Loading data from all pipeline stages...")
        
        # Load Stage 2 results
        if os.path.exists("stage2_results.json"):
            with open("stage2_results.json", "r") as f:
                self.stage2_results = json.load(f)
            print("  ✅ Stage 2 results loaded")
        else:
            print("  ❌ Stage 2 results not found")
            
        # Load Stage 4E results
        if os.path.exists("stage4e_center_results.json"):
            with open("stage4e_center_results.json", "r") as f:
                self.stage4e_results = json.load(f)
            print("  ✅ Stage 4E results loaded")
        else:
            print("  ❌ Stage 4E results not found")
            
        # Load Stage 3 results (trader intent)
        if os.path.exists("stage3_results.json"):
            with open("stage3_results.json", "r") as f:
                self.stage3_results = json.load(f)
            print("  ✅ Stage 3 results loaded")
        else:
            print("  ❌ Stage 3 results not found")
            
        # Load Stage 4D results (calibration) - use stage4_results.json
        if os.path.exists("stage4_results.json"):
            with open("stage4_results.json", "r") as f:
                stage4_data = json.load(f)
                self.stage4d_results = stage4_data.get("stage4d_results", {})
                self.ohlc_data = stage4_data.get("stage4a_results", {}).get("ohlc_data", {})
            print("  ✅ Stage 4D results loaded from stage4_results.json")
            print("  ✅ OHLC data loaded from stage4_results.json")
        else:
            print("  ❌ Stage 4 results not found")
    
    def consolidate_elements(self) -> Dict[str, Any]:
        """Consolidate element data using priority logic"""
        print("🔄 Consolidating element data...")
        
        consolidated_elements = {}
        
        # Get all known elements from Stage 2
        stage2_elements = self._get_stage2_elements()
        stage4e_elements = self._get_stage4e_elements()
        
        print(f"  📊 Stage 2 elements: {len(stage2_elements)}")
        print(f"  📊 Stage 4E elements: {len(stage4e_elements)}")
        
        # Process each element with priority logic
        for element_id in stage2_elements:
            if element_id in stage4e_elements:
                # Use Stage 4E data (primary)
                consolidated_elements[element_id] = self._merge_element_data(
                    element_id,
                    stage2_elements[element_id], 
                    stage4e_elements[element_id],
                    source="stage4e"
                )
                print(f"  ✅ {element_id}: Using Stage 4E data")
            else:
                # Use Stage 2 data (fallback)
                consolidated_elements[element_id] = self._merge_element_data(
                    element_id,
                    stage2_elements[element_id], 
                    None,
                    source="stage2"
                )
                print(f"  📋 {element_id}: Using Stage 2 fallback")
        
        # Add any Stage 4E elements not in Stage 2
        for element_id in stage4e_elements:
            if element_id not in consolidated_elements:
                consolidated_elements[element_id] = self._merge_element_data(
                    None,
                    stage4e_elements[element_id],
                    source="stage4e"
                )
                print(f"  🆕 {element_id}: New Stage 4E element")
        
        return consolidated_elements
    
    def _get_stage2_elements(self) -> Dict[str, Any]:
        """Extract elements from Stage 2 results"""
        elements = {}
        
        # Get elements from stage2a_results (horizontal lines)
        stage2a = self.stage2_results.get("stage2a_results", {})
        for line in stage2a.get("horizontal_lines", []):
            element_id = line.get("element_id")
            if element_id:
                elements[element_id] = {
                    "type": "horizontal_line",
                    "stage2_data": line,
                    "source": "stage2a"
                }
        
        # Get elements from stage2b_results (diagonal lines)
        stage2b = self.stage2_results.get("stage2b_results", {})
        for line in stage2b.get("diagonal_lines", []):
            element_id = line.get("element_id")
            if element_id:
                elements[element_id] = {
                    "type": "diagonal_line",
                    "stage2_data": line,
                    "source": "stage2b"
                }
        
        # Get elements from stage2c_results (zones)
        stage2c = self.stage2_results.get("stage2c_results", {})
        for zone in stage2c.get("zones", []):
            element_id = zone.get("element_id")
            if element_id:
                elements[element_id] = {
                    "type": "zone",
                    "stage2_data": zone,
                    "source": "stage2c"
                }
        
        return elements
    
    def _get_stage4e_elements(self) -> Dict[str, Any]:
        """Extract elements from Stage 4E results, combining multiple clusters for same element ID"""
        elements = {}
        
        stage4e_elements = self.stage4e_results.get("elements", [])
        
        for element in stage4e_elements:
            element_id = element.get("element_id")
            if element_id:
                if element_id in elements:
                    # Combine with existing element (multiple clusters for same element)
                    existing_data = elements[element_id]["stage4e_data"]
                    existing_pixels = existing_data.get("pixels_list", [])
                    new_pixels = element.get("pixels_list", [])
                    
                    # Combine pixel lists
                    combined_pixels = existing_pixels + new_pixels
                    combined_pixel_count = existing_data.get("pixels", 0) + element.get("pixels", 0)
                    
                    # Update the combined element
                    elements[element_id]["stage4e_data"]["pixels_list"] = combined_pixels
                    elements[element_id]["stage4e_data"]["pixels"] = combined_pixel_count
                else:
                    # First occurrence of this element
                    elements[element_id] = {
                        "type": element.get("type"),
                        "stage4e_data": element,
                        "source": "stage4e"
                    }
        
        return elements
    
    def _merge_element_data(self, element_id: str, stage2_data: Optional[Dict], stage4e_data: Optional[Dict], source: str) -> Dict[str, Any]:
        """Merge element data from different stages"""
        merged = {
            "source": source,
            "detection_method": source,
            "confidence": "high" if source == "stage4e" else "medium"
        }
        
        if stage2_data:
            # Flatten nested structure
            actual_data = stage2_data.get("stage2_data", stage2_data)
            # Use the type from stage2_data (set in _get_stage2_elements) instead of actual_data
            merged["element_type"] = stage2_data.get("type", actual_data.get("element_type", "unknown"))
            merged["description"] = actual_data.get("description", actual_data.get("notes", ""))
            merged["grid_location"] = actual_data.get("grid_location", "")
            # Keep raw stage2 data for reference but flatten the main fields
            merged["stage2_source"] = stage2_data.get("source", "stage2")
            merged["stage2_notes"] = actual_data.get("notes", "")
            
            # If no Stage 4E data, try to get detailed detection data from Stage 2 sub-sections
            if not stage4e_data:
                self._add_stage2_detailed_data(merged, element_id, actual_data)
        
        if stage4e_data:
            # Extract from nested structure
            actual_data = stage4e_data.get("stage4e_data", stage4e_data)
            # Set element type from Stage 4E data
            merged["element_type"] = actual_data.get("type", "unknown")
            # Keep essential Stage 4E metadata
            position = actual_data.get("position", "")
            if position == "above":
                merged["trend_line_type"] = "resistance"
            elif position == "below":
                merged["trend_line_type"] = "support"
            else:
                merged["trend_line_type"] = ""
            merged["stage4e_confidence"] = actual_data.get("confidence", 0.0)
            
            # For diagonal lines, generate clean path structure
            if merged["element_type"] == "diagonal_line":
                diagonal_path = self._generate_diagonal_path(element_id, stage4e_data, stage2_data)
                # Clean structure: only essential diagonal data
                merged["path_points"] = diagonal_path.get("path_points", [])
                merged["boundary_rectangle"] = diagonal_path.get("boundary_rectangle", {})
                merged["line_equation"] = diagonal_path.get("line_equation", {})
                # Add price/time mapping for diagonal path points
                merged["price_time_points"] = self._path_points_to_price_time(diagonal_path.get("path_points", []))
            else:
                # For other elements, keep detailed pixel data and detection info
                merged["pixel_coordinates"] = actual_data.get("pixels_list", [])
                merged["pixel_count"] = actual_data.get("pixels", 0)
                
                # Add element-specific detection details
                if merged["element_type"] == "horizontal_line":
                    y_detected = actual_data.get("y_detected", 0)
                    merged["y_detected"] = y_detected
                    merged["price"] = self._y_to_price(y_detected)
                    merged["columns"] = actual_data.get("columns", [])
                elif merged["element_type"] == "zone":
                    y_top = actual_data.get("y_top_detected", 0)
                    y_bottom = actual_data.get("y_bottom_detected", 0)
                    x_range = actual_data.get("x_range", [])
                    
                    merged["y_top_detected"] = y_top
                    merged["y_bottom_detected"] = y_bottom
                    merged["price_top"] = self._y_to_price(y_top)
                    merged["price_bottom"] = self._y_to_price(y_bottom)
                    merged["x_range"] = x_range
                    merged["time_range"] = self._x_range_to_time_range(x_range)
                    merged["columns"] = actual_data.get("columns", [])
        
        return merged
    
    def _generate_diagonal_path(self, element_id: str, stage4e_data: Dict, stage2_data: Dict) -> Dict:
        """
        Generate full diagonal path from cluster centers and rectangle intersections.
        Returns path with at least 4 points: rectangle intersections + cluster centers.
        """
        # Get cluster centers from Stage 4E data
        actual_data = stage4e_data.get("stage4e_data", stage4e_data)
        pixels_list = actual_data.get("pixels_list", [])
        
        if not pixels_list:
            return {"path_points": [], "boundary_rectangle": {}}
        
        # Group pixels into clusters by X-proximity (within 10px)
        clusters = self._group_pixels_into_clusters(pixels_list)
        
        if not clusters:
            return {"path_points": [], "boundary_rectangle": {}}
        
        # Take one representative pixel from each cluster
        cluster_representatives = []
        for cluster in clusters:
            if cluster:  # Non-empty cluster
                # Take the first pixel from each cluster
                cluster_representatives.append(cluster[0])
        
        # Sort cluster representatives by X-coordinate (left to right)
        cluster_representatives.sort(key=lambda p: p[0])
        
        # Get Stage 2B rectangle boundaries
        boundary_rectangle = self._get_stage2b_boundaries(element_id)
        if not boundary_rectangle:
            return {"path_points": cluster_representatives, "boundary_rectangle": {}}
        
        # Generate line through cluster representatives
        if len(cluster_representatives) >= 2:
            # Calculate line equation: y = mx + b
            x1, y1 = cluster_representatives[0]
            x2, y2 = cluster_representatives[-1]
            
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                intercept = y1 - slope * x1
                
                # Find intersections with rectangle boundaries
                intersections = self._find_rectangle_intersections(
                    slope, intercept, boundary_rectangle
                )
                
                # Combine intersections and cluster representatives
                all_points = intersections + cluster_representatives
                
                # Sort all points by X-coordinate
                all_points.sort(key=lambda p: p[0])
                
                return {
                    "path_points": all_points,
                    "boundary_rectangle": boundary_rectangle,
                    "line_equation": {"slope": slope, "intercept": intercept}
                }
        
        # Fallback: just return cluster representatives
        return {
            "path_points": cluster_representatives,
            "boundary_rectangle": boundary_rectangle
        }
    
    def _get_stage2b_boundaries(self, element_id: str) -> Dict:
        """Get Stage 2B rectangle boundaries for an element"""
        stage2b_results = self.stage2_results.get("stage2b_results", {})
        diagonal_lines = stage2b_results.get("diagonal_lines", [])
        
        for diagonal in diagonal_lines:
            if diagonal.get("element_id") == element_id:
                start_cell = diagonal.get("start")  # e.g., "C5"
                end_cell = diagonal.get("end")      # e.g., "F3"
                
                if start_cell and end_cell:
                    return self._convert_grid_to_pixels(start_cell, end_cell)
        
        return {}
    
    def _convert_grid_to_pixels(self, start_cell: str, end_cell: str) -> Dict:
        """Convert grid cells to pixel rectangle boundaries using GridMapper"""
        # Get grid metadata
        grid_metadata = self.stage2_results.get('grid_metadata', {})
        
        # Create GridMapper instance for proper coordinate conversion
        grid_mapper = GridMapper(grid_metadata['grid_cols'], grid_metadata['grid_rows'])
        
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
        
        return {
            "x_min": x1,
            "x_max": x2,
            "y_min": y1,
            "y_max": y2,
            "start_cell": start_cell,
            "end_cell": end_cell
        }
    
    def _find_rectangle_intersections(self, slope: float, intercept: float, rectangle: Dict) -> List[Tuple[int, int]]:
        """Find where line intersects rectangle boundaries"""
        x_min, x_max = rectangle["x_min"], rectangle["x_max"]
        y_min, y_max = rectangle["y_min"], rectangle["y_max"]
        
        intersections = []
        
        # Check intersections with left and right edges (x = x_min, x = x_max)
        for x in [x_min, x_max]:
            y = slope * x + intercept
            if y_min <= y <= y_max:
                intersections.append((int(x), int(y)))
        
        # Check intersections with top and bottom edges (y = y_min, y = y_max)
        for y in [y_min, y_max]:
            if slope != 0:  # Avoid division by zero
                x = (y - intercept) / slope
                if x_min <= x <= x_max:
                    intersections.append((int(x), int(y)))
        
        return intersections
    
    def _group_pixels_into_clusters(self, pixels_list: List[List[int]], x_threshold: int = 10) -> List[List[Tuple[int, int]]]:
        """
        Group pixels into clusters by X-proximity (within x_threshold pixels on X-axis).
        Returns list of clusters, where each cluster is a list of pixels.
        """
        if not pixels_list:
            return []
        
        # Convert to tuples and sort by X-coordinate
        pixels = []
        for pixel in pixels_list:
            if isinstance(pixel, list) and len(pixel) == 2:
                pixels.append((pixel[0], pixel[1]))
        
        pixels.sort(key=lambda p: p[0])  # Sort by X-coordinate
        
        clusters = []
        current_cluster = [pixels[0]]
        
        for i in range(1, len(pixels)):
            current_pixel = pixels[i]
            prev_pixel = pixels[i-1]
            
            # Check if current pixel is within x_threshold of the previous pixel
            if abs(current_pixel[0] - prev_pixel[0]) <= x_threshold:
                # Add to current cluster
                current_cluster.append(current_pixel)
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [current_pixel]
        
        # Add the last cluster
        clusters.append(current_cluster)
        
        return clusters
    
    def _y_to_price(self, y_pixel: int) -> float:
        """Convert Y pixel coordinate to price using calibration"""
        if not self.stage4d_results:
            return 0.0
        
        price_calibration = self.stage4d_results.get("price_calibration", {})
        y_to_price = price_calibration.get("y_to_price", {})
        alpha = y_to_price.get("alpha", 0)
        beta = y_to_price.get("beta", 0)
        
        return alpha * y_pixel + beta
    
    def _x_to_timestamp(self, x_pixel: int) -> float:
        """Convert X pixel coordinate to timestamp using calibration"""
        if not self.stage4d_results:
            return 0.0
        
        temporal_calibration = self.stage4d_results.get("temporal_calibration", {})
        gamma = temporal_calibration.get("gamma", 0)
        delta = temporal_calibration.get("delta", 0)
        
        return gamma * x_pixel + delta
    
    def _x_range_to_time_range(self, x_range: List[int]) -> List[float]:
        """Convert X pixel range to timestamp range"""
        if len(x_range) != 2:
            return [0.0, 0.0]
        
        return [self._x_to_timestamp(x_range[0]), self._x_to_timestamp(x_range[1])]
    
    def _path_points_to_price_time(self, path_points: List[List[int]]) -> List[List[float]]:
        """Convert diagonal path points from [x, y] pixels to [timestamp, price]"""
        price_time_points = []
        for point in path_points:
            if len(point) == 2:
                x, y = point
                timestamp = self._x_to_timestamp(x)
                price = self._y_to_price(y)
                price_time_points.append([timestamp, price])
        
        return price_time_points
    
    def _add_stage2_detailed_data(self, merged: Dict, element_id: str, stage2_data: Dict):
        """Add detailed detection data from Stage 2 sub-sections when Stage 4E is missing"""
        element_type = merged.get("element_type", "unknown")
        
        if element_type == "zone":
            # Look in stage2diii_results for detailed zone data
            stage2diii_results = self.stage2_results.get("stage2diii_results", [])
            for zone in stage2diii_results:
                if zone.get("element_id") == element_id:
                    # Add zone-specific data
                    merged["y_top_detected"] = zone.get("y_top_px", 0)
                    merged["y_bottom_detected"] = zone.get("y_bottom_px", 0)
                    merged["price_top"] = self._y_to_price(zone.get("y_top_px", 0))
                    merged["price_bottom"] = self._y_to_price(zone.get("y_bottom_px", 0))
                    merged["area"] = zone.get("area", "")
                    merged["columns"] = self._area_to_columns(zone.get("area", ""))
                    break
        
        elif element_type == "horizontal_line":
            # Look in stage2di_results for horizontal line data
            stage2di_results = self.stage2_results.get("stage2di_results", [])
            for line in stage2di_results:
                if line.get("element_id") == element_id:
                    # Add horizontal line-specific data
                    y_pixel = line.get("coordinates", {}).get("y_pixel", 0)
                    merged["y_detected"] = y_pixel
                    merged["price"] = self._y_to_price(y_pixel)
                    merged["row"] = line.get("row", "")
                    merged["columns"] = self._row_to_columns(line.get("row", ""))
                    break
        
        elif element_type == "diagonal_line":
            # Look in stage2b_results for diagonal line data
            stage2b_results = self.stage2_results.get("stage2b_results", {})
            diagonal_lines = stage2b_results.get("diagonal_lines", [])
            for diagonal in diagonal_lines:
                if diagonal.get("element_id") == element_id:
                    # Add diagonal-specific data
                    merged["start_cell"] = diagonal.get("start", "")
                    merged["end_cell"] = diagonal.get("end", "")
                    merged["area"] = f"{diagonal.get('start', '')} to {diagonal.get('end', '')}"
                    break
    
    def _area_to_columns(self, area: str) -> List[str]:
        """Convert area like 'A2 to C2' to list of columns ['A', 'B', 'C']"""
        if not area or " to " not in area:
            return []
        
        try:
            start, end = area.split(" to ")
            start_col = start[0]
            end_col = end[0]
            
            columns = []
            for col_ord in range(ord(start_col), ord(end_col) + 1):
                columns.append(chr(col_ord))
            return columns
        except:
            return []
    
    def _row_to_columns(self, row: str) -> List[str]:
        """Convert row to list of columns using dynamic grid metadata"""
        if not row:
            return []
        
        # Get grid metadata to determine column range
        grid_metadata = self.stage2_results.get("grid_metadata", {})
        grid_cols = grid_metadata.get("grid_cols", 8)  # Default to 8 if not found
        
        # Generate column list dynamically (A, B, C, D, E, F, G, H for 8 columns)
        columns = []
        for i in range(grid_cols):
            columns.append(chr(ord('A') + i))
        
        return columns
    
    def create_unified_json(self) -> Dict[str, Any]:
        """Create the unified JSON structure"""
        print("🏗️ Creating unified JSON structure...")
        
        # Consolidate elements
        consolidated_elements = self.consolidate_elements()
        
        # Create unified structure - chart data only
        unified_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "image_path": self.image_path,
                "pipeline_version": "1.0",
                "consolidation_method": "priority_based"
            },
            "chart_data": {
                "grid_metadata": self.stage2_results.get("grid_metadata", {}),
                "calibration": self.stage4d_results,
                "elements": consolidated_elements,
                "ohlc_data": self.ohlc_data
            }
        }
        
        return unified_data
    
    
    def run(self):
        """Run Stage 5A consolidation"""
        print("🚀 Starting Stage 5A: Data Consolidation & Analysis")
        print("=" * 60)
        
        # Load all data
        self.load_all_data()
        
        # Create unified JSON
        unified_data = self.create_unified_json()
        
        # Save results
        output_file = "stage5a_consolidated_results.json"
        with open(output_file, "w") as f:
            json.dump(unified_data, f, indent=2)
        
        print(f"✅ Results saved to {output_file}")
        
        # Print summary
        self._print_summary(unified_data)
        
        return unified_data
    
    def _print_summary(self, data: Dict[str, Any]):
        """Print consolidation summary"""
        print("\n📊 Stage 5A Consolidation Summary:")
        print("=" * 40)
        
        elements = data["chart_data"]["elements"]
        
        # Count elements by type and source
        element_types = {}
        detection_sources = {}
        
        for element_id, element_data in elements.items():
            element_type = element_data.get("element_type", "unknown")
            source = element_data.get("source", "unknown")
            
            element_types[element_type] = element_types.get(element_type, 0) + 1
            detection_sources[source] = detection_sources.get(source, 0) + 1
        
        print(f"📊 Total Elements: {len(elements)}")
        print(f"📊 Element Types: {element_types}")
        print(f"📊 Detection Sources: {detection_sources}")
        
        print("\n🎯 Element Details:")
        for element_id, element_data in elements.items():
            source = element_data.get("source", "unknown")
            confidence = element_data.get("confidence", "unknown")
            element_type = element_data.get("element_type", "unknown")
            print(f"  {element_id}: {element_type} ({source}, {confidence})")
        
        print("\n🎉 Stage 5A consolidation completed!")

if __name__ == "__main__":
    consolidator = Stage5AConsolidation()
    results = consolidator.run()
