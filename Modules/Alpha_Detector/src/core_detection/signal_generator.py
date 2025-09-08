"""
Signal Generator
Phase 1.3.2: Generate trading signals from features, patterns, and regime
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Generates trading signals from features, patterns, and regime data
    """
    
    def __init__(self):
        self.signal_thresholds = {
            'min_confidence': 0.6,  # Production threshold
            'min_strength': 0.5,    # Production threshold
            'min_volume_confirmation': 1.2
        }
        
        # Signal conditions weights
        self.condition_weights = {
            'rsi': 0.2,
            'macd': 0.2,
            'breakout': 0.3,
            'volume': 0.2,
            'regime': 0.1
        }
    
    def generate_signals(self, features, patterns, regime):
        """
        Generate trading signals from features and patterns
        
        Args:
            features (Dict): Extracted features
            patterns (Dict): Detected patterns
            regime (str): Market regime
            
        Returns:
            List[Dict]: Generated signals
        """
        signals = []
        
        try:
            # Generate long signals
            long_signals = self._generate_long_signals(features, patterns, regime)
            signals.extend(long_signals)
            
            # Generate short signals
            short_signals = self._generate_short_signals(features, patterns, regime)
            signals.extend(short_signals)
            
            # Filter signals by quality
            filtered_signals = self._filter_signals_by_quality(signals)
            
            logger.debug(f"Generated {len(filtered_signals)} signals from {len(signals)} candidates")
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return []
    
    def _generate_long_signals(self, features, patterns, regime):
        """Generate long (buy) signals"""
        signals = []
        
        try:
            # Check if conditions are met for long signals
            if self._check_long_conditions(features, patterns, regime):
                signal = self._create_signal('long', features, patterns, regime)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating long signals: {e}")
            return []
    
    def _generate_short_signals(self, features, patterns, regime):
        """Generate short (sell) signals"""
        signals = []
        
        try:
            # Check if conditions are met for short signals
            if self._check_short_conditions(features, patterns, regime):
                signal = self._create_signal('short', features, patterns, regime)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating short signals: {e}")
            return []
    
    def _check_long_conditions(self, features, patterns, regime):
        """Check conditions for long signals"""
        try:
            conditions = []
            
            # RSI condition (not overbought)
            rsi = features.get('rsi', 50)
            if rsi is not None and rsi < 70:
                conditions.append(('rsi', True, 0.8))
            else:
                conditions.append(('rsi', False, 0.0))
            
            # MACD condition (bullish)
            macd_bullish = features.get('macd_bullish', False)
            if macd_bullish:
                conditions.append(('macd', True, 0.9))
            else:
                conditions.append(('macd', False, 0.0))
            
            # Breakout condition (upward breakout)
            breakout_up = patterns.get('breakout_up', False)
            if breakout_up:
                conditions.append(('breakout', True, 0.9))
            else:
                conditions.append(('breakout', False, 0.0))
            
            # Volume condition (volume spike)
            volume_spike = features.get('volume_spike', False)
            if volume_spike:
                conditions.append(('volume', True, 0.8))
            else:
                conditions.append(('volume', False, 0.0))
            
            # Regime condition (suitable for long)
            suitable_regime = regime in ['trending_up', 'ranging', 'ranging_volatile']
            if suitable_regime:
                conditions.append(('regime', True, 0.7))
            else:
                conditions.append(('regime', False, 0.0))
            
            # Calculate weighted score
            total_score = 0.0
            total_weight = 0.0
            
            for condition_name, met, score in conditions:
                weight = self.condition_weights.get(condition_name, 0.1)
                if met:
                    total_score += score * weight
                total_weight += weight
            
            # Require at least 60% weighted score
            return total_score / total_weight >= 0.6 if total_weight > 0 else False
            
        except Exception as e:
            logger.error(f"Error checking long conditions: {e}")
            return False
    
    def _check_short_conditions(self, features, patterns, regime):
        """Check conditions for short signals"""
        try:
            conditions = []
            
            # RSI condition (not oversold)
            rsi = features.get('rsi', 50)
            if rsi is not None and rsi > 30:
                conditions.append(('rsi', True, 0.8))
            else:
                conditions.append(('rsi', False, 0.0))
            
            # MACD condition (bearish)
            macd_bearish = features.get('macd_bearish', False)
            if macd_bearish:
                conditions.append(('macd', True, 0.9))
            else:
                conditions.append(('macd', False, 0.0))
            
            # Breakout condition (downward breakout)
            breakout_down = patterns.get('breakout_down', False)
            if breakout_down:
                conditions.append(('breakout', True, 0.9))
            else:
                conditions.append(('breakout', False, 0.0))
            
            # Volume condition (volume spike)
            volume_spike = features.get('volume_spike', False)
            if volume_spike:
                conditions.append(('volume', True, 0.8))
            else:
                conditions.append(('volume', False, 0.0))
            
            # Regime condition (suitable for short)
            suitable_regime = regime in ['trending_down', 'ranging', 'ranging_volatile']
            if suitable_regime:
                conditions.append(('regime', True, 0.7))
            else:
                conditions.append(('regime', False, 0.0))
            
            # Calculate weighted score
            total_score = 0.0
            total_weight = 0.0
            
            for condition_name, met, score in conditions:
                weight = self.condition_weights.get(condition_name, 0.1)
                if met:
                    total_score += score * weight
                total_weight += weight
            
            # Require at least 60% weighted score
            return total_score / total_weight >= 0.6 if total_weight > 0 else False
            
        except Exception as e:
            logger.error(f"Error checking short conditions: {e}")
            return False
    
    def _create_signal(self, direction, features, patterns, regime):
        """Create a trading signal"""
        try:
            # Calculate confidence and strength
            confidence = self._calculate_confidence(features, patterns, regime, direction)
            strength = self._calculate_strength(features, patterns, regime, direction)
            
            # Only create signal if it meets minimum thresholds
            if confidence < self.signal_thresholds['min_confidence'] or \
               strength < self.signal_thresholds['min_strength']:
                return None
            
            signal = {
                'direction': direction,
                'confidence': confidence,
                'strength': strength,
                'features': self._extract_signal_features(features),
                'patterns': self._extract_signal_patterns(patterns),
                'regime': regime,
                'timestamp': datetime.now(timezone.utc),
                'signal_id': f"{direction}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            return signal
            
        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None
    
    def _calculate_confidence(self, features, patterns, regime, direction):
        """Calculate signal confidence"""
        try:
            confidence_factors = []
            
            # RSI confidence
            rsi = features.get('rsi', 50)
            if rsi is not None:
                if direction == 'long':
                    rsi_conf = max(0, (70 - rsi) / 40)  # Higher confidence when RSI is lower
                else:
                    rsi_conf = max(0, (rsi - 30) / 40)  # Higher confidence when RSI is higher
                confidence_factors.append(rsi_conf)
            
            # MACD confidence
            macd_histogram = features.get('macd_histogram', 0)
            if macd_histogram is not None:
                macd_conf = min(abs(macd_histogram) * 10, 1.0)  # Higher confidence with stronger MACD
                confidence_factors.append(macd_conf)
            
            # Breakout confidence
            breakout_strength = patterns.get('breakout_strength', 0)
            confidence_factors.append(min(breakout_strength, 1.0))
            
            # Volume confidence
            volume_ratio = features.get('volume_ratio', 1.0)
            if volume_ratio is not None:
                vol_conf = min((volume_ratio - 1.0) / 2.0, 1.0)  # Higher confidence with more volume
                confidence_factors.append(vol_conf)
            
            # Regime confidence
            regime_conf = 0.8 if regime in ['trending_up', 'trending_down'] else 0.6
            confidence_factors.append(regime_conf)
            
            # Average confidence
            return np.mean(confidence_factors) if confidence_factors else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _calculate_strength(self, features, patterns, regime, direction):
        """Calculate signal strength"""
        try:
            strength_factors = []
            
            # RSI strength
            rsi = features.get('rsi', 50)
            if rsi is not None:
                if direction == 'long':
                    rsi_strength = max(0, (50 - rsi) / 50)  # Stronger when RSI is lower
                else:
                    rsi_strength = max(0, (rsi - 50) / 50)  # Stronger when RSI is higher
                strength_factors.append(rsi_strength)
            
            # MACD strength
            macd_histogram = features.get('macd_histogram', 0)
            if macd_histogram is not None:
                macd_strength = min(abs(macd_histogram) * 5, 1.0)
                strength_factors.append(macd_strength)
            
            # Breakout strength
            breakout_strength = patterns.get('breakout_strength', 0)
            strength_factors.append(min(breakout_strength, 1.0))
            
            # Volume strength
            volume_ratio = features.get('volume_ratio', 1.0)
            if volume_ratio is not None:
                vol_strength = min((volume_ratio - 1.0) / 3.0, 1.0)
                strength_factors.append(vol_strength)
            
            # Average strength
            return np.mean(strength_factors) if strength_factors else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating strength: {e}")
            return 0.5
    
    def _extract_signal_features(self, features):
        """Extract relevant features for signal"""
        signal_features = {}
        relevant_keys = ['rsi', 'macd', 'macd_signal', 'macd_histogram', 'bb_position', 'volume_ratio']
        
        for key in relevant_keys:
            if key in features:
                signal_features[key] = features[key]
        
        return signal_features
    
    def _extract_signal_patterns(self, patterns):
        """Extract relevant patterns for signal"""
        signal_patterns = {}
        relevant_keys = ['breakout_up', 'breakout_down', 'breakout_strength', 'current_support', 'current_resistance']
        
        for key in relevant_keys:
            if key in patterns:
                signal_patterns[key] = patterns[key]
        
        return signal_patterns
    
    def _filter_signals_by_quality(self, signals):
        """Filter signals by quality thresholds"""
        filtered = []
        
        for signal in signals:
            if (signal.get('confidence', 0) >= self.signal_thresholds['min_confidence'] and
                signal.get('strength', 0) >= self.signal_thresholds['min_strength']):
                filtered.append(signal)
        
        return filtered


if __name__ == "__main__":
    # Test the SignalGenerator
    print("🧪 Testing SignalGenerator...")
    
    # Create sample features and patterns
    features = {
        'rsi': 45.0,
        'macd': 0.001,
        'macd_signal': 0.0005,
        'macd_histogram': 0.0005,
        'macd_bullish': True,
        'macd_bearish': False,
        'bb_position': 0.3,
        'volume_ratio': 1.8,
        'volume_spike': True
    }
    
    patterns = {
        'breakout_up': True,
        'breakout_down': False,
        'breakout_strength': 0.8,
        'current_support': 50000,
        'current_resistance': 52000
    }
    
    regime = 'trending_up'
    
    # Initialize signal generator
    generator = SignalGenerator()
    
    # Generate signals
    signals = generator.generate_signals(features, patterns, regime)
    
    # Display results
    print(f"✅ Signal generation complete!")
    print(f"   Generated {len(signals)} signals")
    
    for i, signal in enumerate(signals):
        print(f"   Signal {i+1}: {signal['direction']} - confidence: {signal['confidence']:.3f}, strength: {signal['strength']:.3f}")
