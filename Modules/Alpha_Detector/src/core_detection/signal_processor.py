"""
Signal Processing System for Alpha Detector
Handles signal filtering, cooldown periods, and quality control
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SignalFilter:
    """Configuration for signal filtering"""
    min_confidence: float = 0.6
    min_strength: float = 0.5
    max_signals_per_symbol: int = 3
    signal_cooldown_minutes: int = 30
    max_signals_per_timeframe: int = 2
    min_volume_confirmation: float = 1.2

class SignalProcessor:
    """
    Processes and filters trading signals with quality control and cooldown management
    """
    
    def __init__(self, signal_filter: Optional[SignalFilter] = None):
        self.signal_filter = signal_filter or SignalFilter()
        self.recent_signals = {}  # Track recent signals per symbol
        self.signal_history = []  # Track all processed signals
        
    def process_signals(self, signals: List[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
        """
        Process and filter signals for a specific symbol
        
        Args:
            signals: List of raw signals from detection engine
            symbol: Trading symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            List of filtered and processed signals
        """
        if not signals:
            return []
        
        logger.info(f"Processing {len(signals)} signals for {symbol}")
        
        # Step 1: Filter by quality thresholds
        quality_filtered = self._filter_by_quality(signals)
        logger.info(f"Quality filtered: {len(quality_filtered)} signals remain")
        
        # Step 2: Filter by cooldown period
        cooldown_filtered = self._filter_by_cooldown(quality_filtered, symbol)
        logger.info(f"Cooldown filtered: {len(cooldown_filtered)} signals remain")
        
        # Step 3: Filter by timeframe limits
        timeframe_filtered = self._filter_by_timeframe_limits(cooldown_filtered)
        logger.info(f"Timeframe filtered: {len(timeframe_filtered)} signals remain")
        
        # Step 4: Limit signals per symbol
        final_signals = self._limit_signals_per_symbol(timeframe_filtered)
        logger.info(f"Final filtered: {len(final_signals)} signals remain")
        
        # Step 5: Update tracking and add metadata
        processed_signals = self._add_processing_metadata(final_signals, symbol)
        
        # Step 6: Update recent signals tracking
        self._update_recent_signals(processed_signals, symbol)
        
        # Step 7: Add to signal history
        self._add_to_history(processed_signals)
        
        return processed_signals
    
    def _filter_by_quality(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter signals by quality thresholds"""
        filtered = []
        
        for signal in signals:
            confidence = signal.get('confidence', 0.0)
            strength = signal.get('strength', 0.0)
            volume_ratio = signal.get('volume_ratio', 1.0)
            
            # Check all quality criteria
            if (confidence >= self.signal_filter.min_confidence and
                strength >= self.signal_filter.min_strength and
                volume_ratio >= self.signal_filter.min_volume_confirmation):
                filtered.append(signal)
            else:
                logger.debug(f"Signal filtered out: confidence={confidence:.2f}, "
                           f"strength={strength:.2f}, volume_ratio={volume_ratio:.2f}")
        
        return filtered
    
    def _filter_by_cooldown(self, signals: List[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
        """Filter signals by cooldown period"""
        if symbol not in self.recent_signals:
            return signals
        
        current_time = datetime.now(timezone.utc)
        cooldown_delta = timedelta(minutes=self.signal_filter.signal_cooldown_minutes)
        
        filtered = []
        for signal in signals:
            last_signal_time = self.recent_signals[symbol].get('last_signal_time')
            
            if (last_signal_time is None or 
                current_time - last_signal_time > cooldown_delta):
                filtered.append(signal)
            else:
                time_since_last = current_time - last_signal_time
                logger.debug(f"Signal filtered by cooldown: {time_since_last} < {cooldown_delta}")
        
        return filtered
    
    def _filter_by_timeframe_limits(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter signals by timeframe limits"""
        timeframe_counts = {}
        filtered = []
        
        for signal in signals:
            timeframe = signal.get('timeframe', 'unknown')
            current_count = timeframe_counts.get(timeframe, 0)
            
            if current_count < self.signal_filter.max_signals_per_timeframe:
                filtered.append(signal)
                timeframe_counts[timeframe] = current_count + 1
            else:
                logger.debug(f"Signal filtered by timeframe limit: {timeframe} has {current_count} signals")
        
        return filtered
    
    def _limit_signals_per_symbol(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Limit number of signals per symbol"""
        return signals[:self.signal_filter.max_signals_per_symbol]
    
    def _add_processing_metadata(self, signals: List[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
        """Add processing metadata to signals"""
        processed = []
        
        for i, signal in enumerate(signals):
            # Add processing metadata
            signal['processing_metadata'] = {
                'processed_at': datetime.now(timezone.utc),
                'symbol': symbol,
                'signal_rank': i + 1,
                'total_signals': len(signals),
                'processor_version': '1.0.0'
            }
            
            # Add quality score
            signal['quality_score'] = self._calculate_quality_score(signal)
            
            processed.append(signal)
        
        return processed
    
    def _calculate_quality_score(self, signal: Dict[str, Any]) -> float:
        """Calculate overall quality score for a signal"""
        confidence = signal.get('confidence', 0.0)
        strength = signal.get('strength', 0.0)
        volume_ratio = signal.get('volume_ratio', 1.0)
        
        # Weighted quality score
        quality_score = (
            confidence * 0.4 +
            strength * 0.3 +
            min(volume_ratio, 2.0) * 0.3  # Cap volume ratio at 2.0
        )
        
        return min(quality_score, 1.0)  # Cap at 1.0
    
    def _update_recent_signals(self, signals: List[Dict[str, Any]], symbol: str):
        """Update recent signals tracking"""
        if signals:
            self.recent_signals[symbol] = {
                'last_signal_time': signals[-1]['timestamp'],
                'signal_count': len(signals),
                'last_quality_score': signals[-1]['quality_score']
            }
    
    def _add_to_history(self, signals: List[Dict[str, Any]]):
        """Add signals to history for analysis"""
        for signal in signals:
            self.signal_history.append({
                'signal': signal,
                'added_at': datetime.now(timezone.utc)
            })
    
    def get_signal_statistics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get signal processing statistics"""
        if symbol:
            recent_data = self.recent_signals.get(symbol, {})
            symbol_history = [s for s in self.signal_history 
                            if s['signal'].get('symbol') == symbol]
        else:
            recent_data = self.recent_signals
            symbol_history = self.signal_history
        
        return {
            'symbol': symbol,
            'recent_signals': recent_data,
            'total_processed': len(symbol_history),
            'active_symbols': len(self.recent_signals),
            'filter_config': {
                'min_confidence': self.signal_filter.min_confidence,
                'min_strength': self.signal_filter.min_strength,
                'cooldown_minutes': self.signal_filter.signal_cooldown_minutes,
                'max_per_symbol': self.signal_filter.max_signals_per_symbol
            }
        }
    
    def update_filter_config(self, new_config: Dict[str, Any]):
        """Update signal filter configuration"""
        for key, value in new_config.items():
            if hasattr(self.signal_filter, key):
                setattr(self.signal_filter, key, value)
                logger.info(f"Updated filter config: {key} = {value}")
            else:
                logger.warning(f"Unknown filter config key: {key}")
    
    def clear_history(self, symbol: Optional[str] = None):
        """Clear signal history"""
        if symbol:
            self.signal_history = [s for s in self.signal_history 
                                 if s['signal'].get('symbol') != symbol]
            if symbol in self.recent_signals:
                del self.recent_signals[symbol]
        else:
            self.signal_history.clear()
            self.recent_signals.clear()
        
        logger.info(f"Cleared signal history for {'symbol' if symbol else 'all symbols'}")
    
    def get_cooldown_status(self, symbol: str) -> Dict[str, Any]:
        """Get cooldown status for a symbol"""
        if symbol not in self.recent_signals:
            return {
                'symbol': symbol,
                'cooldown_active': False,
                'time_remaining': 0,
                'last_signal_time': None
            }
        
        last_signal_time = self.recent_signals[symbol].get('last_signal_time')
        if not last_signal_time:
            return {
                'symbol': symbol,
                'cooldown_active': False,
                'time_remaining': 0,
                'last_signal_time': None
            }
        
        current_time = datetime.now(timezone.utc)
        cooldown_delta = timedelta(minutes=self.signal_filter.signal_cooldown_minutes)
        time_since_last = current_time - last_signal_time
        
        cooldown_active = time_since_last < cooldown_delta
        time_remaining = max(0, (cooldown_delta - time_since_last).total_seconds() / 60)
        
        return {
            'symbol': symbol,
            'cooldown_active': cooldown_active,
            'time_remaining': time_remaining,
            'last_signal_time': last_signal_time,
            'cooldown_duration_minutes': self.signal_filter.signal_cooldown_minutes
        }

# =============================================
# USAGE EXAMPLES
# =============================================

def example_usage():
    """Example usage of SignalProcessor"""
    
    # Create signal processor with custom config
    custom_filter = SignalFilter(
        min_confidence=0.7,
        min_strength=0.6,
        signal_cooldown_minutes=45,
        max_signals_per_symbol=2
    )
    
    processor = SignalProcessor(custom_filter)
    
    # Example signals
    signals = [
        {
            'direction': 'long',
            'confidence': 0.8,
            'strength': 0.7,
            'volume_ratio': 1.5,
            'timeframe': '1h',
            'timestamp': datetime.now(timezone.utc)
        },
        {
            'direction': 'short',
            'confidence': 0.6,
            'strength': 0.5,
            'volume_ratio': 1.1,
            'timeframe': '15m',
            'timestamp': datetime.now(timezone.utc)
        }
    ]
    
    # Process signals
    processed = processor.process_signals(signals, 'BTC')
    print(f"Processed {len(processed)} signals")
    
    # Get statistics
    stats = processor.get_signal_statistics('BTC')
    print(f"Signal statistics: {stats}")
    
    # Check cooldown status
    cooldown_status = processor.get_cooldown_status('BTC')
    print(f"Cooldown status: {cooldown_status}")

if __name__ == "__main__":
    example_usage()

