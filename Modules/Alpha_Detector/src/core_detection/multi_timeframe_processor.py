"""
Multi-Timeframe Data Processor
Phase 1.3.1: Roll up 1-minute OHLCV data to multiple timeframes
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class MultiTimeframeProcessor:
    """
    Processes 1-minute OHLCV data into multiple timeframes for analysis
    """
    
    def __init__(self):
        self.timeframes = {
            '1m': '1min',   # Entry signals, noise filtering
            '5m': '5min',   # Short-term momentum
            '15m': '15min', # Medium-term trend
            '1h': '1h'      # Long-term trend confirmation
        }
        self.min_data_points = {
            '1m': 100,   # 100 minutes
            '5m': 100,   # 500 minutes (8+ hours)
            '15m': 100,  # 1500 minutes (25+ hours)
            '1h': 100    # 100 hours (4+ days)
        }
    
    def process_multi_timeframe(self, data_1m):
        """
        Process 1m data into multiple timeframes
        
        Args:
            data_1m (pd.DataFrame): 1-minute OHLCV data with columns:
                - timestamp, open, high, low, close, volume
        
        Returns:
            dict: Dictionary with timeframe names as keys and processed data as values
        """
        results = {}
        
        for tf_name, tf_freq in self.timeframes.items():
            # Roll up 1m data to target timeframe
            ohlc_data = self._roll_up_ohlc(data_1m, tf_freq)
            
            # Check if we have enough data
            if len(ohlc_data) < self.min_data_points[tf_name]:
                logger.warning(f"Insufficient data for {tf_name}: {len(ohlc_data)} < {self.min_data_points[tf_name]}")
                continue
            
            results[tf_name] = {
                'ohlc': ohlc_data,
                'timeframe': tf_name,
                'data_points': len(ohlc_data)
            }
        
        return results
    
    def _roll_up_ohlc(self, data_1m, target_freq):
        """
        Roll up 1-minute data to target frequency
        
        Args:
            data_1m (pd.DataFrame): 1-minute OHLCV data
            target_freq (str): Target frequency (e.g., '5min', '15min', '1h')
        
        Returns:
            pd.DataFrame: Rolled-up OHLCV data
        """
        # Ensure we have a copy to avoid modifying original data
        data = data_1m.copy()
        
        # Set timestamp as index for resampling
        data_indexed = data.set_index('timestamp')
        
        # Resample to target frequency
        resampled = data_indexed.resample(target_freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Reset index to get timestamp back as column
        return resampled.reset_index()
    
    def get_timeframe_info(self):
        """
        Get information about supported timeframes
        
        Returns:
            dict: Timeframe information
        """
        return {
            'supported_timeframes': list(self.timeframes.keys()),
            'frequencies': self.timeframes,
            'min_data_points': self.min_data_points
        }


def create_sample_market_data():
    """
    Create sample market data for testing
    """
    # Generate 1000+ data points for higher timeframes
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
    
    # Generate realistic price data with trends
    np.random.seed(42)
    base_price = 50000
    
    # Create different trend periods
    trend_periods = [
        (0, 200, 0.001),    # Upward trend
        (200, 400, -0.0005), # Downward trend
        (400, 600, 0.0002),  # Sideways
        (600, 800, 0.0015),  # Strong upward
        (800, 1000, -0.0008) # Correction
    ]
    
    prices = [base_price]
    for i in range(1, 1000):
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
        'volume': np.random.uniform(100, 1000, 1000)
    }
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Test the MultiTimeframeProcessor
    print("🧪 Testing MultiTimeframeProcessor...")
    
    # Create sample data
    sample_data = create_sample_market_data()
    print(f"✅ Created sample data: {len(sample_data)} data points")
    
    # Initialize processor
    processor = MultiTimeframeProcessor()
    
    # Process multi-timeframe data
    mtf_data = processor.process_multi_timeframe(sample_data)
    
    # Display results
    print(f"✅ Multi-timeframe processing complete!")
    for tf_name, tf_data in mtf_data.items():
        print(f"   {tf_name}: {tf_data['data_points']} data points")
    
    # Show timeframe info
    info = processor.get_timeframe_info()
    print(f"✅ Supported timeframes: {info['supported_timeframes']}")

