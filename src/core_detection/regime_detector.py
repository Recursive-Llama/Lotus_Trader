"""
Regime Detector
Phase 1.3.2: Market regime detection (trending, ranging, volatility, volume)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Detects current market regime from OHLCV data and features
    """
    
    def __init__(self):
        self.regime_thresholds = {
            'trending_up': 0.6,
            'trending_down': -0.6,
            'ranging': 0.2
        }
        self.lookback_periods = {
            'short': 20,
            'medium': 50,
            'long': 100
        }
        self.volatility_thresholds = {
            'high': 1.5,
            'low': 0.5
        }
        self.volume_thresholds = {
            'high': 1.5,
            'low': 0.5
        }
    
    def detect_regime(self, market_data, features):
        """
        Detect current market regime
        
        Args:
            market_data (pd.DataFrame): OHLCV data
            features (Dict): Extracted features
            
        Returns:
            Dict: Regime detection results
        """
        try:
            if len(market_data) < 20:
                return self._get_default_regime()
            
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(market_data)
            
            # Calculate volatility regime
            volatility_regime = self._calculate_volatility_regime(market_data)
            
            # Calculate volume regime
            volume_regime = self._calculate_volume_regime(market_data)
            
            # Combine indicators to determine regime
            regime = self._combine_regime_indicators(trend_strength, volatility_regime, volume_regime)
            
            # Calculate overall confidence
            confidence = self._calculate_regime_confidence(trend_strength, volatility_regime, volume_regime)
            
            return {
                'regime': regime,
                'trend_strength': trend_strength,
                'volatility_regime': volatility_regime,
                'volume_regime': volume_regime,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return self._get_default_regime()
    
    def _calculate_trend_strength(self, market_data):
        """Calculate trend strength using multiple timeframes"""
        try:
            prices = market_data['close']
            
            if len(prices) < self.lookback_periods['long']:
                return 0.0
            
            # Short-term trend (20 periods)
            short_trend = 0.0
            if len(prices) >= self.lookback_periods['short']:
                short_trend = (prices.iloc[-1] - prices.iloc[-self.lookback_periods['short']]) / prices.iloc[-self.lookback_periods['short']]
            
            # Medium-term trend (50 periods)
            medium_trend = 0.0
            if len(prices) >= self.lookback_periods['medium']:
                medium_trend = (prices.iloc[-1] - prices.iloc[-self.lookback_periods['medium']]) / prices.iloc[-self.lookback_periods['medium']]
            
            # Long-term trend (100 periods)
            long_trend = 0.0
            if len(prices) >= self.lookback_periods['long']:
                long_trend = (prices.iloc[-1] - prices.iloc[-self.lookback_periods['long']]) / prices.iloc[-self.lookback_periods['long']]
            
            # Weighted average (more weight to shorter timeframes)
            trend_strength = (0.5 * short_trend + 0.3 * medium_trend + 0.2 * long_trend)
            
            return trend_strength
            
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return 0.0
    
    def _calculate_volatility_regime(self, market_data):
        """Calculate volatility regime"""
        try:
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 50:
                return 'normal_volatility'
            
            # Current volatility (20 periods)
            current_vol = returns.rolling(20).std().iloc[-1]
            
            # Historical volatility (100 periods)
            historical_vol = returns.rolling(100).std().iloc[-1]
            
            # Volatility ratio
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
            
            if vol_ratio > self.volatility_thresholds['high']:
                return 'high_volatility'
            elif vol_ratio < self.volatility_thresholds['low']:
                return 'low_volatility'
            else:
                return 'normal_volatility'
                
        except Exception as e:
            logger.error(f"Error calculating volatility regime: {e}")
            return 'normal_volatility'
    
    def _calculate_volume_regime(self, market_data):
        """Calculate volume regime"""
        try:
            volume = market_data['volume']
            
            if len(volume) < 20:
                return 'normal_volume'
            
            # Current volume vs average
            current_vol = volume.iloc[-1]
            avg_vol = volume.rolling(20).mean().iloc[-1]
            
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            if vol_ratio > self.volume_thresholds['high']:
                return 'high_volume'
            elif vol_ratio < self.volume_thresholds['low']:
                return 'low_volume'
            else:
                return 'normal_volume'
                
        except Exception as e:
            logger.error(f"Error calculating volume regime: {e}")
            return 'normal_volume'
    
    def _combine_regime_indicators(self, trend_strength, volatility_regime, volume_regime):
        """Combine indicators to determine final regime"""
        try:
            # Primary regime based on trend strength
            if trend_strength > self.regime_thresholds['trending_up']:
                return 'trending_up'
            elif trend_strength < self.regime_thresholds['trending_down']:
                return 'trending_down'
            else:
                # Secondary classification based on volatility and volume
                if volatility_regime == 'high_volatility' and volume_regime == 'high_volume':
                    return 'ranging_volatile'
                elif volatility_regime == 'low_volatility' and volume_regime == 'low_volume':
                    return 'ranging_quiet'
                else:
                    return 'ranging'
                    
        except Exception as e:
            logger.error(f"Error combining regime indicators: {e}")
            return 'unknown'
    
    def _calculate_regime_confidence(self, trend_strength, volatility_regime, volume_regime):
        """Calculate confidence in regime detection"""
        try:
            confidence = 0.5  # Base confidence
            
            # Trend strength confidence
            abs_trend = abs(trend_strength)
            if abs_trend > 0.1:
                confidence += min(abs_trend * 0.5, 0.3)
            
            # Volatility regime confidence
            if volatility_regime in ['high_volatility', 'low_volatility']:
                confidence += 0.1
            
            # Volume regime confidence
            if volume_regime in ['high_volume', 'low_volume']:
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating regime confidence: {e}")
            return 0.5
    
    def _get_default_regime(self):
        """Get default regime values when detection fails"""
        return {
            'regime': 'unknown',
            'trend_strength': 0.0,
            'volatility_regime': 'normal_volatility',
            'volume_regime': 'normal_volume',
            'confidence': 0.0
        }
    
    def get_regime_description(self, regime):
        """Get human-readable description of regime"""
        descriptions = {
            'trending_up': 'Strong upward trend',
            'trending_down': 'Strong downward trend',
            'ranging': 'Sideways movement',
            'ranging_volatile': 'Sideways with high volatility',
            'ranging_quiet': 'Sideways with low volatility',
            'unknown': 'Unknown regime'
        }
        return descriptions.get(regime, 'Unknown regime')
    
    def is_trending_regime(self, regime):
        """Check if regime is trending"""
        return regime in ['trending_up', 'trending_down']
    
    def is_ranging_regime(self, regime):
        """Check if regime is ranging"""
        return regime in ['ranging', 'ranging_volatile', 'ranging_quiet']


if __name__ == "__main__":
    # Test the RegimeDetector
    print("🧪 Testing RegimeDetector...")
    
    # Create sample data
    from .multi_timeframe_processor import create_sample_market_data
    sample_data = create_sample_market_data()
    print(f"✅ Created sample data: {len(sample_data)} data points")
    
    # Initialize regime detector
    detector = RegimeDetector()
    
    # Create dummy features
    features = {}
    
    # Detect regime
    regime = detector.detect_regime(sample_data, features)
    
    # Display results
    print(f"✅ Regime detection complete!")
    print(f"   Regime: {regime['regime']} ({detector.get_regime_description(regime['regime'])})")
    print(f"   Trend strength: {regime['trend_strength']:.4f}")
    print(f"   Volatility: {regime['volatility_regime']}")
    print(f"   Volume: {regime['volume_regime']}")
    print(f"   Confidence: {regime['confidence']:.3f}")
    
    # Test regime classification
    print(f"   Is trending: {detector.is_trending_regime(regime['regime'])}")
    print(f"   Is ranging: {detector.is_ranging_regime(regime['regime'])}")
