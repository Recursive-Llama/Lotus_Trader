"""
Multi-Timeframe Signal Combiner
Phase 1.3.2: Combine signals across multiple timeframes with configurable weights
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MultiTimeframeSignalCombiner:
    """
    Combines signals across multiple timeframes using configurable weights
    """
    
    def __init__(self, config=None):
        # Default weights - can be overridden by config
        self.timeframe_weights = {
            '1h': 0.4,   # Long-term trend (highest weight)
            '15m': 0.3,  # Medium-term momentum
            '5m': 0.2,   # Short-term entry
            '1m': 0.1    # Noise filtering (lowest weight)
        }
        self.confirmation_threshold = 0.6  # Require 60% timeframes to agree
        
        # Load configuration if provided
        if config:
            self.load_configuration(config)
    
    def load_configuration(self, config):
        """Load timeframe weights and thresholds from configuration"""
        try:
            if 'timeframe_weights' in config:
                self.timeframe_weights.update(config['timeframe_weights'])
                self._validate_weights()
            
            if 'confirmation_threshold' in config:
                self.confirmation_threshold = config['confirmation_threshold']
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def _validate_weights(self):
        """Validate that weights sum to 1.0"""
        total_weight = sum(self.timeframe_weights.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Timeframe weights must sum to 1.0, got {total_weight}")
    
    def update_weights(self, new_weights):
        """Update timeframe weights dynamically"""
        try:
            self.timeframe_weights.update(new_weights)
            self._validate_weights()
            logger.info(f"Updated timeframe weights: {self.timeframe_weights}")
        except Exception as e:
            logger.error(f"Error updating weights: {e}")
    
    def get_weight_summary(self):
        """Get current weight configuration summary"""
        return {
            'timeframe_weights': self.timeframe_weights.copy(),
            'confirmation_threshold': self.confirmation_threshold,
            'total_weight': sum(self.timeframe_weights.values())
        }
    
    def combine_signals(self, mtf_signals):
        """
        Combine signals across multiple timeframes
        
        Args:
            mtf_signals (Dict): Dictionary with timeframe names as keys and signal lists as values
            
        Returns:
            List[Dict]: Combined signals
        """
        try:
            if not mtf_signals:
                return []
            
            combined_signals = []
            
            # Group signals by direction
            long_signals = self._group_signals_by_direction(mtf_signals, 'long')
            short_signals = self._group_signals_by_direction(mtf_signals, 'short')
            
            # Process long signals
            if long_signals:
                combined_long = self._combine_direction_signals(long_signals, 'long')
                if combined_long:
                    combined_signals.append(combined_long)
            
            # Process short signals
            if short_signals:
                combined_short = self._combine_direction_signals(short_signals, 'short')
                if combined_short:
                    combined_signals.append(combined_short)
            
            logger.debug(f"Combined {len(combined_signals)} signals from {len(mtf_signals)} timeframes")
            return combined_signals
            
        except Exception as e:
            logger.error(f"Error combining signals: {e}")
            return []
    
    def _group_signals_by_direction(self, mtf_signals, direction):
        """Group signals by direction across timeframes"""
        grouped = {}
        
        for tf_name, signals in mtf_signals.items():
            direction_signals = [s for s in signals if s.get('direction') == direction]
            if direction_signals:
                grouped[tf_name] = direction_signals
        
        return grouped
    
    def _combine_direction_signals(self, direction_signals, direction):
        """Combine signals of the same direction across timeframes"""
        if not direction_signals:
            return None
        
        try:
            # Calculate weighted confidence and strength
            total_weight = 0
            weighted_confidence = 0
            weighted_strength = 0
            
            timeframe_confirmations = []
            source_signals = {}
            
            for tf_name, signals in direction_signals.items():
                if tf_name not in self.timeframe_weights:
                    continue
                
                weight = self.timeframe_weights[tf_name]
                
                # Use the strongest signal from this timeframe
                best_signal = max(signals, key=lambda s: s.get('confidence', 0) * s.get('strength', 0))
                
                weighted_confidence += best_signal.get('confidence', 0) * weight
                weighted_strength += best_signal.get('strength', 0) * weight
                total_weight += weight
                
                timeframe_confirmations.append(tf_name)
                source_signals[tf_name] = best_signal
            
            if total_weight == 0:
                return None
            
            # Calculate final metrics
            final_confidence = weighted_confidence / total_weight
            final_strength = weighted_strength / total_weight
            
            # Check confirmation threshold
            confirmation_ratio = len(timeframe_confirmations) / len(self.timeframe_weights)
            
            if confirmation_ratio < self.confirmation_threshold:
                logger.debug(f"Signal rejected: confirmation ratio {confirmation_ratio:.2f} < threshold {self.confirmation_threshold}")
                return None
            
            # Create combined signal
            combined_signal = {
                'direction': direction,
                'confidence': final_confidence,
                'strength': final_strength,
                'timeframe_confirmations': timeframe_confirmations,
                'confirmation_ratio': confirmation_ratio,
                'source_signals': source_signals,
                'timestamp': datetime.now(timezone.utc),
                'signal_id': f"combined_{direction}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            return combined_signal
            
        except Exception as e:
            logger.error(f"Error combining direction signals: {e}")
            return None
    
    def get_combined_signal_summary(self, combined_signal):
        """Get summary of a combined signal"""
        if not combined_signal:
            return {}
        
        return {
            'direction': combined_signal.get('direction'),
            'confidence': combined_signal.get('confidence', 0),
            'strength': combined_signal.get('strength', 0),
            'timeframe_confirmations': combined_signal.get('timeframe_confirmations', []),
            'confirmation_ratio': combined_signal.get('confirmation_ratio', 0),
            'num_timeframes': len(combined_signal.get('timeframe_confirmations', [])),
            'timestamp': combined_signal.get('timestamp')
        }


# Configuration examples
CONSERVATIVE_WEIGHTS = {
    'timeframe_weights': {
        '1h': 0.5,   # 50% - Heavy emphasis on long-term trend
        '15m': 0.3,  # 30% - Medium-term confirmation
        '5m': 0.15,  # 15% - Short-term entry
        '1m': 0.05   # 5% - Minimal noise
    },
    'confirmation_threshold': 0.7  # Require 70% agreement
}

AGGRESSIVE_WEIGHTS = {
    'timeframe_weights': {
        '1h': 0.2,   # 20% - Basic trend context
        '15m': 0.3,  # 30% - Medium-term momentum
        '5m': 0.35,  # 35% - Short-term signals
        '1m': 0.15   # 15% - Entry precision
    },
    'confirmation_threshold': 0.5  # Require 50% agreement
}

BALANCED_WEIGHTS = {
    'timeframe_weights': {
        '1h': 0.4,   # 40% - Long-term trend
        '15m': 0.3,  # 30% - Medium-term momentum
        '5m': 0.2,   # 20% - Short-term entry
        '1m': 0.1    # 10% - Noise filtering
    },
    'confirmation_threshold': 0.6  # Require 60% agreement
}


def get_volatility_adaptive_weights(current_volatility):
    """Adjust weights based on current market volatility"""
    if current_volatility > 0.02:  # High volatility
        return {
            'timeframe_weights': {
                '1h': 0.6,   # 60% - More weight to longer timeframes
                '15m': 0.25, # 25% - Reduce noise
                '5m': 0.1,   # 10% - Minimal short-term
                '1m': 0.05   # 5% - Almost no noise
            },
            'confirmation_threshold': 0.8  # Require 80% agreement
        }
    else:  # Low volatility
        return {
            'timeframe_weights': {
                '1h': 0.3,   # 30% - Less emphasis on trend
                '15m': 0.3,  # 30% - Medium-term
                '5m': 0.25,  # 25% - More short-term
                '1m': 0.15   # 15% - More precision needed
            },
            'confirmation_threshold': 0.5  # Require 50% agreement
        }


if __name__ == "__main__":
    # Test the MultiTimeframeSignalCombiner
    print("🧪 Testing MultiTimeframeSignalCombiner...")
    
    # Create sample multi-timeframe signals
    mtf_signals = {
        '1m': [
            {'direction': 'long', 'confidence': 0.7, 'strength': 0.6, 'timestamp': datetime.now()},
            {'direction': 'short', 'confidence': 0.5, 'strength': 0.4, 'timestamp': datetime.now()}
        ],
        '5m': [
            {'direction': 'long', 'confidence': 0.8, 'strength': 0.7, 'timestamp': datetime.now()}
        ],
        '15m': [
            {'direction': 'long', 'confidence': 0.9, 'strength': 0.8, 'timestamp': datetime.now()}
        ],
        '1h': [
            {'direction': 'long', 'confidence': 0.6, 'strength': 0.5, 'timestamp': datetime.now()}
        ]
    }
    
    # Initialize combiner with balanced weights
    combiner = MultiTimeframeSignalCombiner(BALANCED_WEIGHTS)
    
    # Combine signals
    combined_signals = combiner.combine_signals(mtf_signals)
    
    # Display results
    print(f"✅ Signal combination complete!")
    print(f"   Combined {len(combined_signals)} signals")
    
    for i, signal in enumerate(combined_signals):
        summary = combiner.get_combined_signal_summary(signal)
        print(f"   Signal {i+1}: {summary['direction']} - confidence: {summary['confidence']:.3f}, strength: {summary['strength']:.3f}")
        print(f"      Timeframes: {summary['timeframe_confirmations']}")
        print(f"      Confirmation ratio: {summary['confirmation_ratio']:.2f}")
    
    # Test weight summary
    weight_summary = combiner.get_weight_summary()
    print(f"\n✅ Weight configuration:")
    print(f"   Timeframe weights: {weight_summary['timeframe_weights']}")
    print(f"   Confirmation threshold: {weight_summary['confirmation_threshold']}")
    print(f"   Total weight: {weight_summary['total_weight']}")

