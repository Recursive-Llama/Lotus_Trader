"""
Test Multi-Timeframe Processor with enough data for all timeframes
"""

import sys
import os
sys.path.append('src/core_detection')

from multi_timeframe_processor import MultiTimeframeProcessor
import pandas as pd
import numpy as np

def create_full_sample_data():
    """Create sample data with enough points for all timeframes"""
    # Generate 10000+ data points (7+ days of 1m data)
    dates = pd.date_range(start='2024-01-01', periods=10000, freq='1min')
    
    # Generate realistic price data with trends
    np.random.seed(42)
    base_price = 50000
    
    # Create different trend periods
    trend_periods = [
        (0, 2000, 0.001),      # Upward trend
        (2000, 4000, -0.0005), # Downward trend
        (4000, 6000, 0.0002),  # Sideways
        (6000, 8000, 0.0015),  # Strong upward
        (8000, 10000, -0.0008) # Correction
    ]
    
    prices = [base_price]
    for i in range(1, 10000):
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
        'volume': np.random.uniform(100, 1000, 10000)
    }
    
    return pd.DataFrame(data)

def test_all_timeframes():
    """Test all timeframes with sufficient data"""
    print("🧪 Testing All Timeframes with Sufficient Data")
    print("=" * 60)
    
    # Create full sample data
    sample_data = create_full_sample_data()
    print(f"✅ Created full sample data: {len(sample_data)} data points")
    print(f"   Time range: {sample_data['timestamp'].min()} to {sample_data['timestamp'].max()}")
    
    # Initialize processor
    processor = MultiTimeframeProcessor()
    
    # Process multi-timeframe data
    mtf_data = processor.process_multi_timeframe(sample_data)
    
    # Display results
    print(f"\n✅ Multi-timeframe processing complete!")
    print(f"   Processed {len(mtf_data)} timeframes:")
    
    expected_timeframes = ['1m', '5m', '15m', '1h']
    for tf in expected_timeframes:
        if tf in mtf_data:
            tf_data = mtf_data[tf]
            ohlc = tf_data['ohlc']
            print(f"   ✅ {tf}: {tf_data['data_points']} data points")
            print(f"      Price range: ${ohlc['close'].min():.2f} - ${ohlc['close'].max():.2f}")
        else:
            print(f"   ❌ {tf}: Not processed (insufficient data)")
    
    # Test data structure
    print(f"\n🔍 Data Structure Validation:")
    for tf_name, tf_data in mtf_data.items():
        ohlc = tf_data['ohlc']
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in ohlc.columns]
        
        if not missing_columns:
            print(f"   ✅ {tf_name}: All required columns present")
        else:
            print(f"   ❌ {tf_name}: Missing columns: {missing_columns}")
    
    # Test OHLCV data integrity
    print(f"\n🔍 OHLCV Data Integrity:")
    for tf_name, tf_data in mtf_data.items():
        ohlc = tf_data['ohlc']
        
        # Check OHLC relationships
        invalid_ohlc = (ohlc['high'] < ohlc['low']) | (ohlc['high'] < ohlc['open']) | (ohlc['high'] < ohlc['close']) | (ohlc['low'] > ohlc['open']) | (ohlc['low'] > ohlc['close'])
        invalid_count = invalid_ohlc.sum()
        
        if invalid_count == 0:
            print(f"   ✅ {tf_name}: OHLCV data integrity valid")
        else:
            print(f"   ❌ {tf_name}: {invalid_count} invalid OHLCV bars")
    
    return mtf_data

if __name__ == "__main__":
    test_all_timeframes()
