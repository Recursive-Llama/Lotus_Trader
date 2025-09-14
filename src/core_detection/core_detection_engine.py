"""
Core Detection Engine
Phase 1.3.2: Main multi-timeframe signal detection pipeline
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
from typing import Dict, List, Any

from .multi_timeframe_processor import MultiTimeframeProcessor
from .feature_extractors import BasicFeatureExtractor
from .pattern_detectors import PatternDetector
from .regime_detector import RegimeDetector
from .signal_generator import SignalGenerator
from .multi_timeframe_signal_combiner import MultiTimeframeSignalCombiner
from .signal_processor import SignalProcessor, SignalFilter

# Trading plan generation imports
from trading_plans import TradingPlanBuilder, SignalPackGenerator

# Communication imports
from communication import DirectTableCommunicator, ModuleListener

logger = logging.getLogger(__name__)


class CoreDetectionEngine:
    """
    Main multi-timeframe signal detection pipeline
    Integrates all detection components for comprehensive signal analysis
    """
    
    def __init__(self, db_manager=None, signal_filter=None, enable_trading_plans=True, enable_communication=True):
        self.db_manager = db_manager
        self.multi_timeframe_processor = MultiTimeframeProcessor()
        self.feature_extractors = BasicFeatureExtractor()
        self.pattern_detectors = PatternDetector()
        self.regime_detector = RegimeDetector()
        self.signal_generator = SignalGenerator()
        self.signal_combiner = MultiTimeframeSignalCombiner()
        self.signal_processor = SignalProcessor(signal_filter)
        
        # Trading plan generation components
        self.enable_trading_plans = enable_trading_plans
        if self.enable_trading_plans:
            self.trading_plan_builder = TradingPlanBuilder()
            self.signal_pack_generator = SignalPackGenerator()
        
        # Communication components
        self.enable_communication = enable_communication
        if self.enable_communication:
            self.communicator = DirectTableCommunicator(db_manager)
            self.listener = ModuleListener(db_manager)
        
        # Detection configuration
        self.min_confidence_threshold = 0.6
        self.min_strength_threshold = 0.5
        
    def detect_signals(self, market_data_1m):
        """
        Main multi-timeframe signal detection pipeline with optional trading plan generation
        
        Args:
            market_data_1m (pd.DataFrame): 1-minute OHLCV data
            
        Returns:
            Dict or List[Dict]: If trading plans enabled, returns dict with signals, trading_plans, and signal_packs.
                               If disabled, returns list of signals only.
        """
        try:
            logger.info("Starting multi-timeframe signal detection")
            
            # 1. Process multi-timeframe data
            logger.debug("Processing multi-timeframe data...")
            mtf_data = self.multi_timeframe_processor.process_multi_timeframe(market_data_1m)
            
            if not mtf_data or len(mtf_data) == 0:
                logger.warning("No timeframes processed - insufficient data")
                if self.enable_trading_plans:
                    return {'signals': [], 'trading_plans': [], 'signal_packs': []}
                return []
            
            # 2. Extract features for each timeframe
            logger.debug("Extracting multi-timeframe features...")
            mtf_features = self._extract_multi_timeframe_features(mtf_data)
            
            # 3. Detect patterns for each timeframe
            logger.debug("Detecting multi-timeframe patterns...")
            mtf_patterns = self._detect_multi_timeframe_patterns(mtf_data, mtf_features)
            
            # 4. Determine regime for each timeframe
            logger.debug("Detecting multi-timeframe regimes...")
            mtf_regimes = self._detect_multi_timeframe_regimes(mtf_data, mtf_features)
            
            # 5. Generate signals for each timeframe
            logger.debug("Generating multi-timeframe signals...")
            mtf_signals = self._generate_multi_timeframe_signals(mtf_features, mtf_patterns, mtf_regimes)
            
            # 6. Combine signals across timeframes
            logger.debug("Combining multi-timeframe signals...")
            combined_signals = self.signal_combiner.combine_signals(mtf_signals)
            
            # 7. Process and filter signals
            logger.debug("Processing and filtering signals...")
            symbol = market_data_1m.get('symbol', 'UNKNOWN').iloc[0] if 'symbol' in market_data_1m.columns else 'UNKNOWN'
            final_signals = self.signal_processor.process_signals(combined_signals, symbol)
            
            # 8. Generate trading plans and signal packs (if enabled)
            if self.enable_trading_plans:
                logger.debug("Generating trading plans and signal packs...")
                trading_plans = []
                signal_packs = []
                
                if final_signals:
                    for signal in final_signals:
                        # Generate trading plan
                        trading_plan = self.trading_plan_builder.build_trading_plan(signal, market_data_1m)
                        if trading_plan:
                            trading_plans.append(trading_plan)
                            
                            # Generate signal pack
                            signal_pack = self.signal_pack_generator.generate_signal_pack(
                                signal, trading_plan, market_data_1m
                            )
                            if signal_pack:
                                signal_packs.append(signal_pack)
                
                # 9. Publish trading plans to Decision Maker (if communication enabled)
                if self.enable_communication and trading_plans and signal_packs:
                    logger.debug("Publishing trading plans to Decision Maker...")
                    published_ids = self.communicator.publish_multiple_trading_plans(trading_plans, signal_packs)
                    logger.info(f"Published {len(published_ids)} trading plans to Decision Maker")
                
                logger.info(f"Signal detection complete: {len(final_signals)} signals, {len(trading_plans)} trading plans, {len(signal_packs)} signal packs")
                
                return {
                    'signals': final_signals,
                    'trading_plans': trading_plans,
                    'signal_packs': signal_packs
                }
            else:
                logger.info(f"Signal detection complete: {len(final_signals)} final signals")
                return final_signals
            
        except Exception as e:
            logger.error(f"Error in signal detection: {e}")
            if self.enable_trading_plans:
                return {'signals': [], 'trading_plans': [], 'signal_packs': []}
            return []
    
    def get_trading_plans(self, market_data_1m):
        """
        Get only trading plans from the detection pipeline
        
        Args:
            market_data_1m (pd.DataFrame): 1-minute OHLCV data
            
        Returns:
            List[TradingPlan]: List of trading plans
        """
        if not self.enable_trading_plans:
            logger.warning("Trading plans not enabled")
            return []
        
        result = self.detect_signals(market_data_1m)
        if isinstance(result, dict):
            return result.get('trading_plans', [])
        return []
    
    def get_signal_packs(self, market_data_1m):
        """
        Get only signal packs from the detection pipeline
        
        Args:
            market_data_1m (pd.DataFrame): 1-minute OHLCV data
            
        Returns:
            List[SignalPack]: List of signal packs
        """
        if not self.enable_trading_plans:
            logger.warning("Trading plans not enabled")
            return []
        
        result = self.detect_signals(market_data_1m)
        if isinstance(result, dict):
            return result.get('signal_packs', [])
        return []
    
    def get_signals_only(self, market_data_1m):
        """
        Get only signals from the detection pipeline (disable trading plan generation)
        
        Args:
            market_data_1m (pd.DataFrame): 1-minute OHLCV data
            
        Returns:
            List[Dict]: List of signals
        """
        # Temporarily disable trading plans
        original_enable = self.enable_trading_plans
        self.enable_trading_plans = False
        
        try:
            result = self.detect_signals(market_data_1m)
            return result if isinstance(result, list) else result.get('signals', [])
        finally:
            # Restore original setting
            self.enable_trading_plans = original_enable
    
    def start_communication(self, check_interval: float = 5.0):
        """
        Start communication with other modules
        
        Args:
            check_interval: Seconds between database checks for incoming messages
        """
        if not self.enable_communication:
            logger.warning("Communication not enabled")
            return False
        
        try:
            self.listener.start_listening(check_interval)
            logger.info("Communication started - listening for feedback from Decision Maker and Trader")
            return True
        except Exception as e:
            logger.error(f"Error starting communication: {e}")
            return False
    
    def stop_communication(self):
        """Stop communication with other modules"""
        if not self.enable_communication:
            logger.warning("Communication not enabled")
            return
        
        try:
            self.listener.stop_listening()
            logger.info("Communication stopped")
        except Exception as e:
            logger.error(f"Error stopping communication: {e}")
    
    def get_communication_status(self) -> Dict[str, Any]:
        """Get communication status and statistics"""
        if not self.enable_communication:
            return {'enabled': False, 'error': 'Communication not enabled'}
        
        try:
            communicator_status = self.communicator.get_communication_status()
            listener_status = self.listener.get_listener_status()
            
            return {
                'enabled': True,
                'communicator': communicator_status,
                'listener': listener_status,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {'enabled': True, 'error': str(e)}
    
    def get_feedback_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent feedback from other modules"""
        if not self.enable_communication:
            return []
        
        try:
            return self.listener.get_feedback_history(limit)
        except Exception as e:
            logger.error(f"Error getting feedback history: {e}")
            return []
    
    def _extract_multi_timeframe_features(self, mtf_data):
        """Extract features for all timeframes on-demand"""
        mtf_features = {}
        
        for tf_name, tf_data in mtf_data.items():
            try:
                # Calculate all features on-demand from raw OHLCV data
                features = self.feature_extractors.extract_all_features(tf_data['ohlc'])
                mtf_features[tf_name] = features
                logger.debug(f"Extracted {len(features)} features for {tf_name}")
            except Exception as e:
                logger.error(f"Error extracting features for {tf_name}: {e}")
                mtf_features[tf_name] = {}
        
        return mtf_features
    
    def _detect_multi_timeframe_patterns(self, mtf_data, mtf_features):
        """Detect patterns for all timeframes"""
        mtf_patterns = {}
        
        for tf_name, tf_data in mtf_data.items():
            try:
                patterns = self.pattern_detectors.detect_all_patterns(
                    tf_data['ohlc'], 
                    mtf_features[tf_name]
                )
                mtf_patterns[tf_name] = patterns
                logger.debug(f"Detected patterns for {tf_name}")
            except Exception as e:
                logger.error(f"Error detecting patterns for {tf_name}: {e}")
                mtf_patterns[tf_name] = {}
        
        return mtf_patterns
    
    def _detect_multi_timeframe_regimes(self, mtf_data, mtf_features):
        """Detect regime for all timeframes"""
        mtf_regimes = {}
        
        for tf_name, tf_data in mtf_data.items():
            try:
                regime = self.regime_detector.detect_regime(
                    tf_data['ohlc'], 
                    mtf_features[tf_name]
                )
                mtf_regimes[tf_name] = regime
                logger.debug(f"Detected regime for {tf_name}: {regime.get('regime', 'unknown')}")
            except Exception as e:
                logger.error(f"Error detecting regime for {tf_name}: {e}")
                mtf_regimes[tf_name] = {'regime': 'unknown', 'confidence': 0.0}
        
        return mtf_regimes
    
    def _generate_multi_timeframe_signals(self, mtf_features, mtf_patterns, mtf_regimes):
        """Generate signals for all timeframes"""
        mtf_signals = {}
        
        for tf_name in mtf_features.keys():
            try:
                signals = self.signal_generator.generate_signals(
                    mtf_features[tf_name],
                    mtf_patterns[tf_name],
                    mtf_regimes[tf_name]['regime']
                )
                mtf_signals[tf_name] = signals
                logger.debug(f"Generated {len(signals)} signals for {tf_name}")
            except Exception as e:
                logger.error(f"Error generating signals for {tf_name}: {e}")
                mtf_signals[tf_name] = []
        
        return mtf_signals
    
    def get_detection_summary(self, signals):
        """
        Get summary of detection results
        
        Args:
            signals (List[Dict]): List of detected signals
            
        Returns:
            Dict: Summary statistics
        """
        if not signals:
            return {
                'total_signals': 0,
                'long_signals': 0,
                'short_signals': 0,
                'avg_confidence': 0.0,
                'avg_strength': 0.0
            }
        
        long_signals = [s for s in signals if s.get('direction') == 'long']
        short_signals = [s for s in signals if s.get('direction') == 'short']
        
        avg_confidence = np.mean([s.get('confidence', 0) for s in signals])
        avg_strength = np.mean([s.get('strength', 0) for s in signals])
        
        return {
            'total_signals': len(signals),
            'long_signals': len(long_signals),
            'short_signals': len(short_signals),
            'avg_confidence': avg_confidence,
            'avg_strength': avg_strength
        }
    
    def validate_detection_quality(self, signals):
        """
        Validate the quality of detected signals
        
        Args:
            signals (List[Dict]): List of detected signals
            
        Returns:
            Dict: Quality validation results
        """
        if not signals:
            return {'valid': False, 'issues': ['No signals detected']}
        
        issues = []
        
        # Check confidence thresholds
        low_confidence = [s for s in signals if s.get('confidence', 0) < self.min_confidence_threshold]
        if low_confidence:
            issues.append(f"{len(low_confidence)} signals below confidence threshold")
        
        # Check strength thresholds
        low_strength = [s for s in signals if s.get('strength', 0) < self.min_strength_threshold]
        if low_strength:
            issues.append(f"{len(low_strength)} signals below strength threshold")
        
        # Check for required fields
        missing_fields = []
        for i, signal in enumerate(signals):
            required_fields = ['direction', 'confidence', 'strength', 'timestamp']
            missing = [field for field in required_fields if field not in signal]
            if missing:
                missing_fields.append(f"Signal {i}: missing {missing}")
        
        if missing_fields:
            issues.extend(missing_fields)
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'total_signals': len(signals)
        }
    
    def get_signal_processor_stats(self, symbol=None):
        """Get signal processor statistics"""
        return self.signal_processor.get_signal_statistics(symbol)
    
    def get_cooldown_status(self, symbol):
        """Get cooldown status for a symbol"""
        return self.signal_processor.get_cooldown_status(symbol)
    
    def update_signal_filter(self, new_config):
        """Update signal filter configuration"""
        self.signal_processor.update_filter_config(new_config)
    
    def clear_signal_history(self, symbol=None):
        """Clear signal history"""
        self.signal_processor.clear_history(symbol)


def create_sample_market_data():
    """Create sample market data for testing"""
    from .multi_timeframe_processor import create_sample_market_data
    return create_sample_market_data()


if __name__ == "__main__":
    # Test the Core Detection Engine
    print("🧪 Testing Core Detection Engine...")
    
    # Create sample data
    sample_data = create_sample_market_data()
    print(f"✅ Created sample data: {len(sample_data)} data points")
    
    # Initialize detection engine
    engine = CoreDetectionEngine()
    
    # Detect signals
    signals = engine.detect_signals(sample_data)
    
    # Display results
    summary = engine.get_detection_summary(signals)
    print(f"✅ Detection complete!")
    print(f"   Total signals: {summary['total_signals']}")
    print(f"   Long signals: {summary['long_signals']}")
    print(f"   Short signals: {summary['short_signals']}")
    print(f"   Avg confidence: {summary['avg_confidence']:.3f}")
    print(f"   Avg strength: {summary['avg_strength']:.3f}")
    
    # Validate quality
    quality = engine.validate_detection_quality(signals)
    if quality['valid']:
        print(f"✅ Signal quality validation passed")
    else:
        print(f"❌ Signal quality issues: {quality['issues']}")
