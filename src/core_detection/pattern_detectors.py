"""
Pattern Detectors
Phase 1.3.2: Pattern detection for support/resistance, breakouts, and divergences
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Detects various market patterns from OHLCV data and features
    """
    
    def __init__(self):
        self.support_resistance_detector = SupportResistanceDetector()
        self.breakout_detector = BreakoutDetector()
        self.divergence_detector = DivergenceDetector()
    
    def detect_all_patterns(self, ohlc_data, features):
        """
        Detect all patterns from OHLCV data and features
        
        Args:
            ohlc_data (pd.DataFrame): OHLCV data
            features (Dict): Extracted features
            
        Returns:
            Dict: All detected patterns
        """
        patterns = {}
        
        try:
            # Detect support and resistance levels
            patterns.update(self.detect_support_resistance(ohlc_data))
            
            # Detect breakout patterns
            patterns.update(self.detect_breakouts(ohlc_data, patterns))
            
            # Detect divergences
            patterns.update(self.detect_divergences(ohlc_data, features))
            
            logger.debug(f"Detected {len(patterns)} pattern types")
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {e}")
            patterns = self._get_default_patterns()
        
        return patterns
    
    def detect_support_resistance(self, ohlc_data):
        """Detect horizontal support and resistance levels"""
        try:
            levels = self.support_resistance_detector.find_levels(ohlc_data)
            
            patterns = {
                'support_levels': levels['support'],
                'resistance_levels': levels['resistance'],
                'current_support': self._find_nearest_support(ohlc_data, levels['support']),
                'current_resistance': self._find_nearest_resistance(ohlc_data, levels['resistance']),
                'support_strength': self._calculate_level_strength(levels['support'], ohlc_data['volume']),
                'resistance_strength': self._calculate_level_strength(levels['resistance'], ohlc_data['volume'])
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting support/resistance: {e}")
            return self._get_default_support_resistance()
    
    def detect_breakouts(self, ohlc_data, support_resistance_patterns):
        """Detect breakout patterns"""
        try:
            breakouts = self.breakout_detector.detect(ohlc_data, support_resistance_patterns)
            
            patterns = {
                'breakout_up': breakouts['up'],
                'breakout_down': breakouts['down'],
                'breakout_volume_confirmation': breakouts['volume_confirmed'],
                'breakout_strength': breakouts['strength']
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting breakouts: {e}")
            return self._get_default_breakouts()
    
    def detect_divergences(self, ohlc_data, features):
        """Detect price-indicator divergences"""
        try:
            divergences = self.divergence_detector.detect(ohlc_data, features)
            
            patterns = {
                'bullish_divergence': divergences['bullish'],
                'bearish_divergence': divergences['bearish'],
                'divergence_strength': divergences['strength']
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting divergences: {e}")
            return self._get_default_divergences()
    
    def _find_nearest_support(self, ohlc_data, support_levels):
        """Find nearest support level to current price"""
        if not support_levels or len(ohlc_data) == 0:
            return None
        
        current_price = ohlc_data['close'].iloc[-1]
        valid_supports = [level for level in support_levels if level < current_price]
        
        if not valid_supports:
            return None
        
        return max(valid_supports)
    
    def _find_nearest_resistance(self, ohlc_data, resistance_levels):
        """Find nearest resistance level to current price"""
        if not resistance_levels or len(ohlc_data) == 0:
            return None
        
        current_price = ohlc_data['close'].iloc[-1]
        valid_resistances = [level for level in resistance_levels if level > current_price]
        
        if not valid_resistances:
            return None
        
        return min(valid_resistances)
    
    def _calculate_level_strength(self, levels, volume_data):
        """Calculate strength of support/resistance levels based on volume"""
        if not levels:
            return 0.0
        
        # Simple strength calculation based on number of touches
        # In a real implementation, this would be more sophisticated
        return min(len(levels) / 10.0, 1.0)
    
    def _get_default_patterns(self):
        """Get default pattern values when detection fails"""
        return {
            **self._get_default_support_resistance(),
            **self._get_default_breakouts(),
            **self._get_default_divergences()
        }
    
    def _get_default_support_resistance(self):
        return {
            'support_levels': [],
            'resistance_levels': [],
            'current_support': None,
            'current_resistance': None,
            'support_strength': 0.0,
            'resistance_strength': 0.0
        }
    
    def _get_default_breakouts(self):
        return {
            'breakout_up': False,
            'breakout_down': False,
            'breakout_volume_confirmation': False,
            'breakout_strength': 0.0
        }
    
    def _get_default_divergences(self):
        return {
            'bullish_divergence': False,
            'bearish_divergence': False,
            'divergence_strength': 0.0
        }


class SupportResistanceDetector:
    """Detects support and resistance levels"""
    
    def __init__(self):
        self.min_touches = 2
        self.tolerance = 0.02  # 2% tolerance for level detection
    
    def find_levels(self, ohlc_data):
        """Find support and resistance levels"""
        try:
            if len(ohlc_data) < 20:
                return {'support': [], 'resistance': []}
            
            # Use pivot points to find potential levels
            highs = ohlc_data['high']
            lows = ohlc_data['low']
            
            # Find local maxima and minima
            resistance_candidates = self._find_local_maxima(highs)
            support_candidates = self._find_local_minima(lows)
            
            # Group similar levels
            resistance_levels = self._group_levels(resistance_candidates, highs)
            support_levels = self._group_levels(support_candidates, lows)
            
            return {
                'support': support_levels,
                'resistance': resistance_levels
            }
            
        except Exception as e:
            logger.error(f"Error finding support/resistance levels: {e}")
            return {'support': [], 'resistance': []}
    
    def _find_local_maxima(self, series, window=5):
        """Find local maxima in a series"""
        maxima = []
        for i in range(window, len(series) - window):
            if all(series.iloc[i] >= series.iloc[i-j] for j in range(1, window+1)) and \
               all(series.iloc[i] >= series.iloc[i+j] for j in range(1, window+1)):
                maxima.append(series.iloc[i])
        return maxima
    
    def _find_local_minima(self, series, window=5):
        """Find local minima in a series"""
        minima = []
        for i in range(window, len(series) - window):
            if all(series.iloc[i] <= series.iloc[i-j] for j in range(1, window+1)) and \
               all(series.iloc[i] <= series.iloc[i+j] for j in range(1, window+1)):
                minima.append(series.iloc[i])
        return minima
    
    def _group_levels(self, candidates, price_series):
        """Group similar price levels together"""
        if not candidates:
            return []
        
        # Sort candidates
        candidates = sorted(candidates)
        grouped = []
        current_group = [candidates[0]]
        
        for i in range(1, len(candidates)):
            # If within tolerance, add to current group
            if abs(candidates[i] - current_group[-1]) / current_group[-1] <= self.tolerance:
                current_group.append(candidates[i])
            else:
                # Start new group
                if len(current_group) >= self.min_touches:
                    grouped.append(np.mean(current_group))
                current_group = [candidates[i]]
        
        # Add final group
        if len(current_group) >= self.min_touches:
            grouped.append(np.mean(current_group))
        
        return grouped


class BreakoutDetector:
    """Detects breakout patterns"""
    
    def __init__(self):
        self.breakout_threshold = 0.01  # 1% breakout threshold
        self.volume_multiplier = 1.5    # Volume must be 1.5x average
    
    def detect(self, ohlc_data, support_resistance_patterns):
        """Detect breakout patterns"""
        try:
            if len(ohlc_data) < 10:
                return self._get_default_breakout()
            
            current_price = ohlc_data['close'].iloc[-1]
            current_volume = ohlc_data['volume'].iloc[-1]
            avg_volume = ohlc_data['volume'].rolling(20).mean().iloc[-1]
            
            # Check for resistance breakout
            resistance_levels = support_resistance_patterns.get('resistance_levels', [])
            breakout_up = False
            if resistance_levels:
                nearest_resistance = min([r for r in resistance_levels if r > current_price], default=None)
                if nearest_resistance and (current_price - nearest_resistance) / nearest_resistance > self.breakout_threshold:
                    breakout_up = True
            
            # Check for support breakout
            support_levels = support_resistance_patterns.get('support_levels', [])
            breakout_down = False
            if support_levels:
                nearest_support = max([s for s in support_levels if s < current_price], default=None)
                if nearest_support and (nearest_support - current_price) / nearest_support > self.breakout_threshold:
                    breakout_down = True
            
            # Volume confirmation
            volume_confirmed = current_volume > avg_volume * self.volume_multiplier if avg_volume > 0 else False
            
            # Calculate breakout strength
            strength = 0.0
            if breakout_up or breakout_down:
                strength = min(current_volume / avg_volume if avg_volume > 0 else 1.0, 2.0)
            
            return {
                'up': breakout_up,
                'down': breakout_down,
                'volume_confirmed': volume_confirmed,
                'strength': strength
            }
            
        except Exception as e:
            logger.error(f"Error detecting breakouts: {e}")
            return self._get_default_breakout()
    
    def _get_default_breakout(self):
        return {
            'up': False,
            'down': False,
            'volume_confirmed': False,
            'strength': 0.0
        }


class DivergenceDetector:
    """Detects price-indicator divergences"""
    
    def __init__(self):
        self.lookback_period = 20
    
    def detect(self, ohlc_data, features):
        """Detect divergences between price and indicators"""
        try:
            if len(ohlc_data) < self.lookback_period:
                return self._get_default_divergence()
            
            prices = ohlc_data['close']
            
            # Get recent price and indicator data
            recent_prices = prices.tail(self.lookback_period)
            recent_rsi = features.get('rsi')
            
            # Simple divergence detection
            bullish_divergence = False
            bearish_divergence = False
            strength = 0.0
            
            if recent_rsi is not None:
                # Check for bullish divergence (price makes lower low, RSI makes higher low)
                price_trend = recent_prices.iloc[-1] - recent_prices.iloc[-10]
                rsi_trend = recent_rsi - features.get('rsi', recent_rsi)  # Simplified
                
                if price_trend < 0 and rsi_trend > 0:
                    bullish_divergence = True
                    strength = abs(rsi_trend) / 100.0
                elif price_trend > 0 and rsi_trend < 0:
                    bearish_divergence = True
                    strength = abs(rsi_trend) / 100.0
            
            return {
                'bullish': bullish_divergence,
                'bearish': bearish_divergence,
                'strength': min(strength, 1.0)
            }
            
        except Exception as e:
            logger.error(f"Error detecting divergences: {e}")
            return self._get_default_divergence()
    
    def _get_default_divergence(self):
        return {
            'bullish': False,
            'bearish': False,
            'strength': 0.0
        }


if __name__ == "__main__":
    # Test the PatternDetector
    print("🧪 Testing PatternDetector...")
    
    # Create sample data
    from .multi_timeframe_processor import create_sample_market_data
    sample_data = create_sample_market_data()
    print(f"✅ Created sample data: {len(sample_data)} data points")
    
    # Initialize pattern detector
    detector = PatternDetector()
    
    # Create dummy features
    features = {'rsi': 50.0}
    
    # Detect patterns
    patterns = detector.detect_all_patterns(sample_data, features)
    
    # Display results
    print(f"✅ Pattern detection complete!")
    print(f"   Detected {len(patterns)} pattern types")
    
    for pattern_type, pattern_data in patterns.items():
        print(f"   {pattern_type}: {pattern_data}")

