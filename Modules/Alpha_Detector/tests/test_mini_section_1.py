#!/usr/bin/env python3
"""
Mini-Section 1 Test: Feature Extraction
Test the BasicFeatureExtractor with sample data
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from core_detection.feature_extractors import BasicFeatureExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_market_data():
    """Create sample market data for testing"""
    # Generate 100 data points
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    
    # Generate realistic price data with some trend
    np.random.seed(42)
    base_price = 50000
    trend = np.linspace(0, 0.1, 100)  # 10% upward trend
    noise = np.random.normal(0, 0.001, 100)
    returns = trend + noise
    
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate OHLCV data
    data = {
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    return pd.DataFrame(data)

def test_feature_extraction():
    """Test the feature extraction system"""
    print("\n🧪 Mini-Section 1: Feature Extraction Test")
    print("=" * 60)
    
    try:
        # Create sample data
        print("\n1️⃣ Creating sample market data...")
        sample_data = create_sample_market_data()
        print(f"✅ Created sample data: {len(sample_data)} rows")
        print(f"   Price range: ${sample_data['close'].min():.2f} - ${sample_data['close'].max():.2f}")
        print(f"   Volume range: {sample_data['volume'].min():.2f} - {sample_data['volume'].max():.2f}")
        
        # Initialize feature extractor
        print("\n2️⃣ Initializing BasicFeatureExtractor...")
        extractor = BasicFeatureExtractor()
        print("✅ Feature extractor initialized")
        
        # Test price features
        print("\n3️⃣ Testing price feature extraction...")
        price_features = extractor.extract_price_features(sample_data)
        
        required_price_features = [
            'rsi', 'rsi_overbought', 'rsi_oversold',
            'macd', 'macd_signal', 'macd_histogram', 'macd_bullish', 'macd_bearish',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_position', 'bb_squeeze',
            'bb_above_upper', 'bb_below_lower'
        ]
        
        missing_price_features = [f for f in required_price_features if f not in price_features]
        if not missing_price_features:
            print("✅ Price features extracted successfully")
            print(f"   RSI: {price_features['rsi']:.2f}")
            print(f"   MACD: {price_features['macd']:.4f}")
            print(f"   BB Position: {price_features['bb_position']:.2f}")
        else:
            print(f"❌ Missing price features: {missing_price_features}")
            return False
        
        # Test volume features
        print("\n4️⃣ Testing volume feature extraction...")
        volume_features = extractor.extract_volume_features(sample_data['volume'], sample_data['close'])
        
        required_volume_features = [
            'volume_sma_20', 'volume_ratio', 'volume_spike', 'volume_high', 'volume_low',
            'volume_price_trend', 'on_balance_volume', 'volume_momentum_10'
        ]
        
        missing_volume_features = [f for f in required_volume_features if f not in volume_features]
        if not missing_volume_features:
            print("✅ Volume features extracted successfully")
            print(f"   Volume Ratio: {volume_features['volume_ratio']:.2f}")
            print(f"   Volume Spike: {volume_features['volume_spike']}")
            print(f"   OBV: {volume_features['on_balance_volume']:.2f}")
        else:
            print(f"❌ Missing volume features: {missing_volume_features}")
            return False
        
        # Test technical features
        print("\n5️⃣ Testing technical feature extraction...")
        technical_features = extractor.extract_technical_features(sample_data)
        
        required_technical_features = [
            'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'momentum_10', 'momentum_20', 'volatility_20', 'atr_14',
            'price_above_sma_20', 'price_above_sma_50',
            'price_above_ema_12', 'price_above_ema_26',
            'sma_20_above_50', 'ema_12_above_26'
        ]
        
        missing_technical_features = [f for f in required_technical_features if f not in technical_features]
        if not missing_technical_features:
            print("✅ Technical features extracted successfully")
            print(f"   SMA 20: ${technical_features['sma_20']:.2f}")
            print(f"   SMA 50: ${technical_features['sma_50']:.2f}")
            print(f"   Volatility: {technical_features['volatility_20']:.4f}")
            print(f"   ATR: {technical_features['atr_14']:.2f}")
        else:
            print(f"❌ Missing technical features: {missing_technical_features}")
            return False
        
        # Test feature validation
        print("\n6️⃣ Testing feature validation...")
        
        # Check for reasonable RSI values
        if 0 <= price_features['rsi'] <= 100:
            print("✅ RSI values are reasonable")
        else:
            print(f"❌ RSI value out of range: {price_features['rsi']}")
            return False
        
        # Check for reasonable volume ratio
        if volume_features['volume_ratio'] > 0:
            print("✅ Volume ratio is positive")
        else:
            print(f"❌ Volume ratio is negative: {volume_features['volume_ratio']}")
            return False
        
        # Check for reasonable volatility
        if technical_features['volatility_20'] >= 0:
            print("✅ Volatility is non-negative")
        else:
            print(f"❌ Volatility is negative: {technical_features['volatility_20']}")
            return False
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ MINI-SECTION 1 TESTS PASSED!")
        print(f"🎉 Feature extraction working perfectly!")
        print(f"   📊 Price features: {len(price_features)}")
        print(f"   📈 Volume features: {len(volume_features)}")
        print(f"   🔧 Technical features: {len(technical_features)}")
        print(f"   📋 Total features: {len(price_features) + len(volume_features) + len(technical_features)}")
        print("🚀 Ready for Mini-Section 2: Pattern Detection")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_feature_extraction()
    if not success:
        sys.exit(1)
