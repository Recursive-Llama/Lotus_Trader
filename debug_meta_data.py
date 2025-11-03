#!/usr/bin/env python3

import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
from dotenv import load_dotenv
from src.utils.supabase_manager import SupabaseManager

# Load environment variables
load_dotenv('/Users/bruce/Documents/Lotus_Trader⚘⟁/.env')

def plot_meta_data():
    """Plot META price data and geometry features"""
    
    # Get META price data
    supabase = SupabaseManager()
    
    # Fetch 1h price data
    price_result = supabase.client.table('lowcap_price_data_ohlc').select('timestamp,close_native').eq('token_contract', 'METAwkXcqyXKy1AtsSgJ8JiUHwGCafnZL38n3vYmeta').eq('chain', 'solana').eq('timeframe', '1h').order('timestamp', desc=False).execute()
    
    if not price_result.data:
        print("No price data found for META")
        return
    
    # Convert to lists, filtering out zero prices
    valid_data = [row for row in price_result.data if row['close_native'] > 0]
    timestamps = [datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')) for row in valid_data]
    prices = [row['close_native'] for row in valid_data]
    
    print(f"Found {len(prices)} price points")
    print(f"Price range: {min(prices):.8f} to {max(prices):.8f}")
    print(f"First timestamp: {timestamps[0]}")
    print(f"Last timestamp: {timestamps[-1]}")
    
    # Get geometry features
    geom_result = supabase.client.table('lowcap_positions').select('features').eq('token_contract', 'METAwkXcqyXKy1AtsSgJ8JiUHwGCafnZL38n3vYmeta').eq('token_chain', 'solana').eq('status', 'active').execute()
    
    if not geom_result.data:
        print("No geometry data found for META")
        return
    
    features = geom_result.data[0]['features']
    geometry = features.get('geometry', {})
    
    print(f"\nGeometry features:")
    print(f"  Current trend: {geometry.get('current_trend')}")
    print(f"  Swing points: {geometry.get('swing_points')}")
    print(f"  Levels count: {len(geometry.get('levels', {}).get('sr_levels', []))}")
    print(f"  Diagonals count: {len(geometry.get('diagonals', {}))}")
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # Plot 1: Price data
    ax1.plot(timestamps, prices, 'b-', linewidth=2, label='META Price (SOL)')
    ax1.set_title('META Price Data (1h)')
    ax1.set_ylabel('Price (SOL)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=24))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    
    # Plot 2: Geometry levels
    ax2.plot(timestamps, prices, 'b-', linewidth=1, alpha=0.7, label='Price')
    
    # Plot swing points
    if geometry.get('swing_points', {}).get('coordinates'):
        swing_coords = geometry.get('swing_points', {}).get('coordinates', [])
        swing_highs = [sp for sp in swing_coords if sp['type'] == 'high']
        swing_lows = [sp for sp in swing_coords if sp['type'] == 'low']
        
        # Plot swing highs
        for sp in swing_highs:
            swing_time = datetime.fromisoformat(sp['timestamp'].replace('Z', '+00:00'))
            ax2.scatter(swing_time, sp['price'], color='red', marker='^', s=100, alpha=0.8, zorder=10, label='Swing High' if sp == swing_highs[0] else "")
        
        # Plot swing lows  
        for sp in swing_lows:
            swing_time = datetime.fromisoformat(sp['timestamp'].replace('Z', '+00:00'))
            ax2.scatter(swing_time, sp['price'], color='green', marker='v', s=100, alpha=0.8, zorder=10, label='Swing Low' if sp == swing_lows[0] else "")
    
    # Plot S/R levels
    sr_levels = geometry.get('levels', {}).get('sr_levels', [])
    colors = ['red', 'green', 'orange', 'purple', 'brown']
    
    for i, level in enumerate(sr_levels[:5]):  # Show first 5 levels to avoid clutter
        price_level = level['price']
        strength = level['strength']
        color = colors[i % len(colors)]
        ax2.axhline(y=price_level, color=color, linestyle='--', alpha=0.7, 
                   label=f"S/R {price_level:.6f} (strength: {strength})")
    
    # Plot diagonal trendlines
    diagonals = geometry.get('diagonals', {})
    diagonal_colors = ['blue', 'cyan', 'magenta', 'yellow']
    
    for i, (name, diagonal) in enumerate(diagonals.items()):
        slope = diagonal['slope']
        intercept = diagonal['intercept']
        anchor_time = datetime.fromisoformat(diagonal['anchor_time_iso'].replace('Z', '+00:00'))
        confidence = diagonal['confidence']
        trend_type = diagonal['type']
        
        # Calculate trendline values for our time range
        trendline_prices = []
        trendline_times = []
        
        for j, ts in enumerate(timestamps):
            # Calculate time difference from anchor in hours
            time_diff_hours = (ts - anchor_time).total_seconds() / 3600
            # Calculate price at this time: price = intercept + slope * time_diff_hours
            price_at_time = intercept + slope * time_diff_hours
            trendline_prices.append(price_at_time)
            trendline_times.append(ts)
        
        color = diagonal_colors[i % len(diagonal_colors)]
        linestyle = '-' if 'uptrend' in trend_type else '--'
        ax2.plot(trendline_times, trendline_prices, color=color, linestyle=linestyle, 
                alpha=0.8, linewidth=2, label=f"{trend_type} (R²={confidence:.2f})")
    
    ax2.set_title('META Price with S/R Levels')
    ax2.set_ylabel('Price (SOL)')
    ax2.set_xlabel('Time')
    ax2.grid(True, alpha=0.3)
    ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=24))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig('meta_debug_chart.png', dpi=150, bbox_inches='tight')
    print(f"\nChart saved as: meta_debug_chart.png")
    
    # Show some sample data
    print(f"\nSample price data (first 5 points):")
    for i in range(min(5, len(prices))):
        print(f"  {timestamps[i]}: {prices[i]:.8f}")

if __name__ == "__main__":
    plot_meta_data()
