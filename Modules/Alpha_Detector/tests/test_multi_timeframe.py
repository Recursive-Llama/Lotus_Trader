"""
Test Multi-Timeframe Processor with extended data
"""

import sys
import os
sys.path.append('src/core_detection')

from multi_timeframe_processor import MultiTimeframeProcessor, create_sample_market_data
import pandas as pd
import numpy as np

def create_extended_sample_data():
    """Create extended sample data for all timeframes"""
    # Generate 5000+ data points (3+ days of 1m data)
    dates = pd.date_range(start='2024-01-01', periods=5000, freq='1min')
    
    # Generate realistic price data with trends
    np.random.seed(42)
    base_price = 50000
    
    # Create different trend periods
    trend_periods = [
        (0, 1000, 0.001),     # Upward trend
        (1000, 2000, -0.0005), # Downward trend
        (2000, 3000, 0.0002),  # Sideways
        (3000, 4000, 0.0015),  # Strong upward
        (4000, 5000, -0.0008)  # Correction
    ]
    
    prices = [base_price]
    for i in range(1, 5000):
        # Find current trend period
        trend_rate = 0.0001  # Default small positive trend
        for start, end, rate in trend_periods:
            if start <= i < end:
                trend_rate = rate
                break
        
        # Add noise
        noise = np.random.normal(0, 0.001)
        new_price = prices[-1] * (1 + trend_rate + noise)
        prices.append(new_price)
    
    # Generate OHLCV data
    data = {
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, 5000)
    }
    
    return pd.DataFrame(data)

def test_multi_timeframe_processor():
    """Test the Multi-Timeframe Processor with extended data"""
    print("🧪 Testing Multi-Timeframe Processor with Extended Data")
    print("=" * 60)
    
    # Create extended sample data
    sample_data = create_extended_sample_data()
    print(f"✅ Created extended sample data: {len(sample_data)} data points")
    print(f"   Time range: {sample_data['timestamp'].min()} to {sample_data['timestamp'].max()}")
    
    # Initialize processor
    processor = MultiTimeframeProcessor()
    
    # Process multi-timeframe data
    mtf_data = processor.process_multi_timeframe(sample_data)
    
    # Display results
    print(f"\n✅ Multi-timeframe processing complete!")
    print(f"   Processed {len(mtf_data)} timeframes:")
    
    for tf_name, tf_data in mtf_data.items():
        ohlc = tf_data['ohlc']
        print(f"   {tf_name}: {tf_data['data_points']} data points")
        print(f"      Price range: ${ohlc['close'].min():.2f} - ${ohlc['close'].max():.2f}")
        print(f"      Time range: {ohlc['timestamp'].min()} to {ohlc['timestamp'].max()}")
    
    # Show timeframe info
    info = processor.get_timeframe_info()
    print(f"\n✅ Supported timeframes: {info['supported_timeframes']}")
    print(f"✅ Minimum data points required: {info['min_data_points']}")
    
    # Test data quality
    print(f"\n🔍 Data Quality Check:")
    for tf_name, tf_data in mtf_data.items():
        ohlc = tf_data['ohlc']
        # Check for gaps in timestamps
        time_diffs = ohlc['timestamp'].diff().dropna()
        expected_freq = info['frequencies'][tf_name]
        print(f"   {tf_name}: {len(ohlc)} bars, expected frequency: {expected_freq}")
    
    return mtf_data

if __name__ == "__main__":
    test_multi_timeframe_processor()
