#!/usr/bin/env python3
"""
Stage 5B: Chart Rebuilding
==========================

Rebuilds the original chart using:
- OHLC data with proper price/time scales
- Detected elements overlaid with accurate positioning
- Professional styling to match trader annotations

This validates our entire pipeline by recreating the chart
with all detected elements in their correct positions.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import os

class Stage5B_ChartRebuilder:
    def __init__(self, consolidated_data_path: str = "stage5a_consolidated_results.json"):
        """Initialize the chart rebuilder with consolidated data"""
        self.consolidated_data_path = consolidated_data_path
        self.data = None
        self.ohlc_data = None
        self.calibration = None
        self.elements = None
        self.grid_metadata = None
        
        # Chart styling
        self.chart_width = 12
        self.chart_height = 8
        self.dpi = 100
        
    def load_data(self):
        """Load consolidated data from Stage 5A"""
        print("📊 Loading consolidated data...")
        
        with open(self.consolidated_data_path, 'r') as f:
            self.data = json.load(f)
        
        self.ohlc_data = self.data["chart_data"]["ohlc_data"]
        self.calibration = self.data["chart_data"]["calibration"]
        self.elements = self.data["chart_data"]["elements"]
        self.grid_metadata = self.data["chart_data"]["grid_metadata"]
        
        print(f"  ✅ OHLC data: {self.ohlc_data['records_count']} records")
        print(f"  ✅ Elements: {len(self.elements)} detected")
        print(f"  ✅ Calibration: Price & temporal formulas loaded")
        
    def _x_to_timestamp(self, x: float) -> float:
        """Convert X coordinate to timestamp using temporal calibration"""
        gamma = self.calibration["temporal_calibration"]["gamma"]
        delta = self.calibration["temporal_calibration"]["delta"]
        return gamma * x + delta
    
    def _y_to_price(self, y: float) -> float:
        """Convert Y coordinate to price using price calibration"""
        alpha = self.calibration["price_calibration"]["y_to_price"]["alpha"]
        beta = self.calibration["price_calibration"]["y_to_price"]["beta"]
        return alpha * y + beta
    
    def _convert_area_to_pixels(self, area: str) -> Tuple[float, float]:
        """Convert area string (e.g., 'E3 to F3') to pixel X coordinates"""
        if not area or " to " not in area:
            # Default to full chart width if area is invalid
            return 0, self.grid_metadata["image_width"]
        
        try:
            # Parse area string like "E3 to F3"
            start_cell, end_cell = area.split(" to ")
            
            # Convert cell coordinates to pixel coordinates
            # Using the same logic as in Stage 5A
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from pipeline.grid_mapping import GridMapper
            
            grid_mapper = GridMapper(self.grid_metadata['grid_cols'], self.grid_metadata['grid_rows'])
            
            # Parse start cell (e.g., "E3")
            start_col_letter = start_cell[0]  # "E"
            start_row_num = int(start_cell[1])  # 3
            
            # Parse end cell (e.g., "F3") 
            end_col_letter = end_cell[0]  # "F"
            end_row_num = int(end_cell[1])  # 3
            
            # Get pixel coordinates for the rectangle corners
            start_x, _ = grid_mapper.cell_to_pixel(start_col_letter, start_row_num, self.grid_metadata, u=0.0, v=1.0)
            end_x, _ = grid_mapper.cell_to_pixel(end_col_letter, end_row_num, self.grid_metadata, u=1.0, v=1.0)
            
            return start_x, end_x
            
        except Exception as e:
            print(f"  ⚠️ Error converting area '{area}' to pixels: {e}")
            # Default to full chart width
            return 0, self.grid_metadata["image_width"]
    
    def _prepare_ohlc_data(self) -> Tuple[List[datetime], List[float], List[float], List[float], List[float]]:
        """Prepare OHLC data for plotting"""
        ohlcv = self.ohlc_data["ohlcv"]
        
        timestamps = []
        opens = []
        highs = []
        lows = []
        closes = []
        
        for record in ohlcv:
            timestamp_ms, open_price, high_price, low_price, close_price, volume = record
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            
            timestamps.append(timestamp)
            opens.append(open_price)
            highs.append(high_price)
            lows.append(low_price)
            closes.append(close_price)
        
        return timestamps, opens, highs, lows, closes
    
    def _draw_candlesticks(self, ax, timestamps: List[datetime], opens: List[float], 
                          highs: List[float], lows: List[float], closes: List[float]):
        """Draw candlestick chart"""
        print("🕯️ Drawing candlesticks...")
        
        # Convert to numpy arrays for easier manipulation
        timestamps = np.array(timestamps)
        opens = np.array(opens)
        highs = np.array(highs)
        lows = np.array(lows)
        closes = np.array(closes)
        
        # Determine colors
        colors = ['green' if close >= open else 'red' for open, close in zip(opens, closes)]
        
        # Draw candlesticks
        for i, (timestamp, open_price, high_price, low_price, close_price, color) in enumerate(
            zip(timestamps, opens, highs, lows, closes, colors)):
            
            # Body
            body_height = abs(close_price - open_price)
            body_bottom = min(open_price, close_price)
            
            # Draw wick
            ax.plot([timestamp, timestamp], [low_price, high_price], 
                   color='black', linewidth=0.8, alpha=0.7)
            
            # Draw body
            if body_height > 0:
                ax.bar(timestamp, body_height, bottom=body_bottom, 
                      width=timedelta(hours=6), color=color, alpha=0.8, 
                      edgecolor='black', linewidth=0.5)
            else:
                # Doji - just a line
                ax.plot([timestamp - timedelta(hours=3), timestamp + timedelta(hours=3)], 
                       [open_price, open_price], color='black', linewidth=1)
    
    def _draw_horizontal_line(self, ax, element_id: str, element: Dict):
        """Draw horizontal line element"""
        price = element.get("price", 0)
        description = element.get("description", "")
        
        # Get time range from OHLC data
        timestamps = [datetime.fromtimestamp(ts/1000) for ts, _, _, _, _, _ in self.ohlc_data["ohlcv"]]
        start_time = timestamps[0]
        end_time = timestamps[-1]
        
        # Draw horizontal line
        ax.axhline(y=price, color='black', linestyle='-', linewidth=2, alpha=0.8)
        
        # Add label
        ax.text(start_time + timedelta(days=5), price, f"{element_id}: {price:.4f}", 
               fontsize=8, verticalalignment='bottom', 
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        print(f"  📏 {element_id}: Horizontal line at {price:.4f}")
    
    def _draw_diagonal_line(self, ax, element_id: str, element: Dict):
        """Draw diagonal line element"""
        path_points = element.get("path_points", [])
        trend_line_type = element.get("trend_line_type", "")
        description = element.get("description", "")
        
        if not path_points:
            print(f"  ⚠️ {element_id}: No path points available")
            return
        
        # Convert path points to timestamps and prices
        timestamps = []
        prices = []
        
        for point in path_points:
            x, y = point
            # Convert pixel coordinates back to timestamp and price
            timestamp = self._x_to_timestamp(x)
            price = self._y_to_price(y)
            
            # Convert timestamp to datetime
            dt = datetime.fromtimestamp(timestamp)
            timestamps.append(dt)
            prices.append(price)
        
        # Draw diagonal line
        color = 'red' if trend_line_type == 'resistance' else 'blue'
        linestyle = '--' if trend_line_type == 'resistance' else '-'
        
        # Draw diagonal line
        ax.plot(timestamps, prices, color=color, linestyle=linestyle, 
               linewidth=2, alpha=0.8, label=f"{element_id} ({trend_line_type})")
        
        # Add label at midpoint
        mid_idx = len(timestamps) // 2
        ax.text(timestamps[mid_idx], prices[mid_idx], f"{element_id}", 
               fontsize=8, color=color, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        print(f"  📈 {element_id}: {trend_line_type} diagonal line with {len(path_points)} points")
    
    def _draw_zone(self, ax, element_id: str, element: Dict):
        """Draw zone element"""
        price_top = element.get("price_top", 0)
        price_bottom = element.get("price_bottom", 0)
        description = element.get("description", "")
        
        # Zones span the full chart width, just like horizontal lines
        # Use ax.axhspan() to draw a horizontal band across the entire chart
        height = price_top - price_bottom
        
        # Determine zone color based on description
        if "blue" in description.lower():
            color = 'lightblue'
        elif "red" in description.lower():
            color = 'lightcoral'
        else:
            color = 'lightgray'
        
        # Draw horizontal band spanning full chart width
        ax.axhspan(price_bottom, price_top, color=color, alpha=0.3, 
                  edgecolor='black', linewidth=1)
        
        # Add label at a reasonable position (middle of chart)
        # Get the current x-axis limits to position the label
        xlim = ax.get_xlim()
        mid_time = (xlim[0] + xlim[1]) / 2  # Use matplotlib's internal time format
        mid_price = (price_top + price_bottom) / 2
        ax.text(mid_time, mid_price, f"{element_id}\n{price_bottom:.4f}-{price_top:.4f}", 
               fontsize=8, ha='center', va='center',
               bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        print(f"  📦 {element_id}: Zone {price_bottom:.4f}-{price_top:.4f} (full width)")
    
    def _draw_elements(self, ax):
        """Draw all detected elements"""
        print("🎨 Drawing detected elements...")
        
        for element_id, element in self.elements.items():
            element_type = element.get("element_type", "unknown")
            
            if element_type == "horizontal_line":
                self._draw_horizontal_line(ax, element_id, element)
            elif element_type == "diagonal_line":
                self._draw_diagonal_line(ax, element_id, element)
            elif element_type == "zone":
                self._draw_zone(ax, element_id, element)
            else:
                print(f"  ⚠️ {element_id}: Unknown element type '{element_type}'")
    
    def _setup_chart_styling(self, ax, timestamps: List[datetime]):
        """Setup professional chart styling"""
        print("🎨 Setting up chart styling...")
        
        # Set title
        symbol = self.ohlc_data["symbol"]
        timeframe = self.ohlc_data["timeframe"]
        ax.set_title(f"{symbol} - {timeframe} Chart (Rebuilt with Detected Elements)", 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Format x-axis (time)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Format y-axis (price)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.4f}'))
        
        # Set grid
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # Set labels
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Price (USDT)', fontsize=12, fontweight='bold')
        
        # Set margins
        ax.margins(x=0.02, y=0.02)
        
        # Add legend for diagonal lines
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc='upper left', fontsize=8)
    
    def rebuild_chart(self, output_path: str = "stage5b_rebuilt_chart.png"):
        """Rebuild the complete chart with all elements"""
        print("🏗️ Starting Stage 5B: Chart Rebuilding")
        print("=" * 50)
        
        # Load data
        self.load_data()
        
        # Prepare OHLC data
        timestamps, opens, highs, lows, closes = self._prepare_ohlc_data()
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(self.chart_width, self.chart_height), dpi=self.dpi)
        
        # Draw candlesticks
        self._draw_candlesticks(ax, timestamps, opens, highs, lows, closes)
        
        # Draw detected elements
        self._draw_elements(ax)
        
        # Setup styling
        self._setup_chart_styling(ax, timestamps)
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"✅ Chart saved to: {output_path}")
        print("🎉 Stage 5B: Chart Rebuilding completed!")
        
        return output_path

def main():
    """Main execution function"""
    rebuilder = Stage5B_ChartRebuilder()
    output_path = rebuilder.rebuild_chart()
    
    print(f"\n📊 Chart Rebuilding Summary:")
    print(f"  📁 Output: {output_path}")
    print(f"  📈 Elements: {len(rebuilder.elements)} overlaid")
    print(f"  🕯️ Candles: {rebuilder.ohlc_data['records_count']} drawn")
    print(f"  🎯 Validation: Chart rebuilt with detected elements")

if __name__ == "__main__":
    main()
