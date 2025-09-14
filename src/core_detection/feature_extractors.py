"""
Feature Extractors
Phase 1.3.2: On-demand feature calculation from OHLCV data
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BasicFeatureExtractor:
    """
    Extracts technical indicators and features from OHLCV data on-demand
    """
    
    def __init__(self):
        # RSI configuration
        self.rsi_period = 14
        
        # MACD configuration
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        # Bollinger Bands configuration
        self.bb_period = 20
        self.bb_std = 2
        
        # Moving averages
        self.sma_periods = [20, 50, 100]
        self.ema_periods = [12, 26, 50, 100]
        
        # Volume analysis
        self.volume_period = 20
        
        # Momentum and volatility
        self.momentum_periods = [10, 20]
        self.volatility_period = 20
        self.atr_period = 14
    
    def extract_all_features(self, ohlc_data):
        """
        Extract all features from OHLCV data on-demand
        
        Args:
            ohlc_data (pd.DataFrame): OHLCV data with columns: timestamp, open, high, low, close, volume
            
        Returns:
            Dict: All extracted features
        """
        try:
            # Ensure we have enough data
            if len(ohlc_data) < 50:
                logger.warning(f"Insufficient data for feature extraction: {len(ohlc_data)} < 50")
                return {}
            
            # Extract different feature categories
            price_features = self.extract_price_features(ohlc_data)
            volume_features = self.extract_volume_features(ohlc_data)
            technical_features = self.extract_technical_features(ohlc_data)
            
            # Combine all features
            all_features = {**price_features, **volume_features, **technical_features}
            
            logger.debug(f"Extracted {len(all_features)} features")
            return all_features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return {}
    
    def extract_price_features(self, ohlc_data):
        """Extract price-based features (RSI, MACD, Bollinger Bands)"""
        features = {}
        
        try:
            close_prices = ohlc_data['close']
            
            # RSI
            rsi = self._calculate_rsi(close_prices)
            features['rsi'] = rsi.iloc[-1] if not rsi.empty else None
            features['rsi_overbought'] = features['rsi'] > 70 if features['rsi'] is not None else False
            features['rsi_oversold'] = features['rsi'] < 30 if features['rsi'] is not None else False
            
            # MACD
            macd_line, signal_line, histogram = self._calculate_macd(close_prices)
            features['macd'] = macd_line.iloc[-1] if not macd_line.empty else None
            features['macd_signal'] = signal_line.iloc[-1] if not signal_line.empty else None
            features['macd_histogram'] = histogram.iloc[-1] if not histogram.empty else None
            features['macd_bullish'] = features['macd'] > features['macd_signal'] if features['macd'] is not None and features['macd_signal'] is not None else False
            features['macd_bearish'] = features['macd'] < features['macd_signal'] if features['macd'] is not None and features['macd_signal'] is not None else False
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close_prices)
            features['bb_upper'] = bb_upper.iloc[-1] if not bb_upper.empty else None
            features['bb_middle'] = bb_middle.iloc[-1] if not bb_middle.empty else None
            features['bb_lower'] = bb_lower.iloc[-1] if not bb_lower.empty else None
            
            # BB position and squeeze
            if all(features[key] is not None for key in ['bb_upper', 'bb_middle', 'bb_lower']):
                current_price = close_prices.iloc[-1]
                bb_range = features['bb_upper'] - features['bb_lower']
                features['bb_position'] = (current_price - features['bb_lower']) / bb_range if bb_range > 0 else 0.5
                features['bb_squeeze'] = bb_range / features['bb_middle'] < 0.1
            else:
                features['bb_position'] = 0.5
                features['bb_squeeze'] = False
            
        except Exception as e:
            logger.error(f"Error extracting price features: {e}")
            # Set default values
            features.update({
                'rsi': None, 'rsi_overbought': False, 'rsi_oversold': False,
                'macd': None, 'macd_signal': None, 'macd_histogram': None,
                'macd_bullish': False, 'macd_bearish': False,
                'bb_upper': None, 'bb_middle': None, 'bb_lower': None,
                'bb_position': 0.5, 'bb_squeeze': False
            })
        
        return features
    
    def extract_volume_features(self, ohlc_data):
        """Extract volume-based features"""
        features = {}
        
        try:
            volume = ohlc_data['volume']
            close_prices = ohlc_data['close']
            
            # Volume moving average and ratio
            volume_sma = volume.rolling(self.volume_period).mean()
            features['volume_sma_20'] = volume_sma.iloc[-1] if not volume_sma.empty else None
            features['volume_ratio'] = volume.iloc[-1] / features['volume_sma_20'] if features['volume_sma_20'] is not None and features['volume_sma_20'] > 0 else 1.0
            features['volume_spike'] = features['volume_ratio'] > 2.0
            
            # On-Balance Volume (OBV)
            obv = self._calculate_obv(volume, close_prices)
            features['on_balance_volume'] = obv.iloc[-1] if not obv.empty else None
            features['obv_trend_up'] = obv.iloc[-1] > obv.iloc[-5] if len(obv) >= 5 else False
            
            # Volume Price Trend (VPT)
            vpt = self._calculate_vpt(volume, close_prices)
            features['volume_price_trend'] = vpt.iloc[-1] if not vpt.empty else None
            features['vpt_trend_up'] = vpt.iloc[-1] > vpt.iloc[-5] if len(vpt) >= 5 else False
            
        except Exception as e:
            logger.error(f"Error extracting volume features: {e}")
            # Set default values
            features.update({
                'volume_sma_20': None, 'volume_ratio': 1.0, 'volume_spike': False,
                'on_balance_volume': None, 'obv_trend_up': False,
                'volume_price_trend': None, 'vpt_trend_up': False
            })
        
        return features
    
    def extract_technical_features(self, ohlc_data):
        """Extract technical indicator features"""
        features = {}
        
        try:
            close_prices = ohlc_data['close']
            
            # Simple Moving Averages
            for period in self.sma_periods:
                sma = close_prices.rolling(period).mean()
                features[f'sma_{period}'] = sma.iloc[-1] if not sma.empty else None
            
            # Exponential Moving Averages
            for period in self.ema_periods:
                ema = close_prices.ewm(span=period).mean()
                features[f'ema_{period}'] = ema.iloc[-1] if not ema.empty else None
            
            # Moving Average Crossovers
            if features.get('sma_20') is not None and features.get('sma_50') is not None:
                features['sma_20_50_crossover_bullish'] = features['sma_20'] > features['sma_50']
                features['sma_20_50_crossover_bearish'] = features['sma_20'] < features['sma_50']
            else:
                features['sma_20_50_crossover_bullish'] = False
                features['sma_20_50_crossover_bearish'] = False
            
            if features.get('ema_12') is not None and features.get('ema_26') is not None:
                features['ema_12_26_crossover_bullish'] = features['ema_12'] > features['ema_26']
                features['ema_12_26_crossover_bearish'] = features['ema_12'] < features['ema_26']
            else:
                features['ema_12_26_crossover_bullish'] = False
                features['ema_12_26_crossover_bearish'] = False
            
            # Momentum
            for period in self.momentum_periods:
                momentum = close_prices.pct_change(period)
                features[f'momentum_{period}'] = momentum.iloc[-1] if not momentum.empty else None
            
            # Volatility
            returns = close_prices.pct_change()
            volatility = returns.rolling(self.volatility_period).std()
            features['volatility_20'] = volatility.iloc[-1] if not volatility.empty else None
            
            # Average True Range (ATR)
            atr = self._calculate_atr(ohlc_data)
            features['atr_14'] = atr.iloc[-1] if not atr.empty else None
            
        except Exception as e:
            logger.error(f"Error extracting technical features: {e}")
            # Set default values for all technical features
            for period in self.sma_periods:
                features[f'sma_{period}'] = None
            for period in self.ema_periods:
                features[f'ema_{period}'] = None
            features.update({
                'sma_20_50_crossover_bullish': False, 'sma_20_50_crossover_bearish': False,
                'ema_12_26_crossover_bullish': False, 'ema_12_26_crossover_bearish': False
            })
            for period in self.momentum_periods:
                features[f'momentum_{period}'] = None
            features['volatility_20'] = None
            features['atr_14'] = None
        
        return features
    
    def _calculate_rsi(self, prices, period=None):
        """Calculate Relative Strength Index"""
        if period is None:
            period = self.rsi_period
        
        if len(prices) < period + 1:
            return pd.Series(dtype=float)
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices, fast=None, slow=None, signal=None):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if fast is None:
            fast = self.macd_fast
        if slow is None:
            slow = self.macd_slow
        if signal is None:
            signal = self.macd_signal
        
        if len(prices) < slow:
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
        
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, prices, period=None, std=None):
        """Calculate Bollinger Bands"""
        if period is None:
            period = self.bb_period
        if std is None:
            std = self.bb_std
        
        if len(prices) < period:
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
        
        sma = prices.rolling(period).mean()
        std_dev = prices.rolling(period).std()
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
    
    def _calculate_obv(self, volume, prices):
        """Calculate On-Balance Volume"""
        if len(volume) != len(prices):
            return pd.Series(dtype=float)
        
        obv = pd.Series(index=volume.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(volume)):
            if prices.iloc[i] > prices.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif prices.iloc[i] < prices.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def _calculate_vpt(self, volume, prices):
        """Calculate Volume Price Trend"""
        if len(volume) != len(prices):
            return pd.Series(dtype=float)
        
        price_change = prices.pct_change()
        vpt = (volume * price_change).cumsum()
        return vpt
    
    def _calculate_atr(self, ohlc_data, period=None):
        """Calculate Average True Range"""
        if period is None:
            period = self.atr_period
        
        if len(ohlc_data) < 2:
            return pd.Series(dtype=float)
        
        high = ohlc_data['high']
        low = ohlc_data['low']
        close = ohlc_data['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr


if __name__ == "__main__":
    # Test the BasicFeatureExtractor
    print("🧪 Testing BasicFeatureExtractor...")
    
    # Create sample data
    from .multi_timeframe_processor import create_sample_market_data
    sample_data = create_sample_market_data()
    print(f"✅ Created sample data: {len(sample_data)} data points")
    
    # Initialize feature extractor
    extractor = BasicFeatureExtractor()
    
    # Extract features
    features = extractor.extract_all_features(sample_data)
    
    # Display results
    print(f"✅ Feature extraction complete!")
    print(f"   Extracted {len(features)} features")
    
    # Show some key features
    key_features = ['rsi', 'macd', 'bb_position', 'volume_ratio', 'sma_20', 'volatility_20']
    for feature in key_features:
        if feature in features:
            print(f"   {feature}: {features[feature]}")