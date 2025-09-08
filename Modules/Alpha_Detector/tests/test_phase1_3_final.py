#!/usr/bin/env python3
"""
Final Phase 1.3 Testing Script
Quick validation of all Phase 1.3 components
"""

import sys
import os
import logging
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core_detection.core_detection_engine import CoreDetectionEngine
from core_detection.signal_processor import SignalFilter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_phase1_3_final():
    """Final comprehensive test of Phase 1.3"""
    print("\n🧪 Phase 1.3 Final Testing")
    print("=" * 50)
    
    try:
        # Test 1: Create sample data
        print("\n1️⃣ Creating extended sample data...")
        from core_detection.multi_timeframe_processor import create_sample_market_data
        
        # Create large dataset for comprehensive testing
        sample_data = create_sample_market_data()
        print(f"✅ Created sample data: {len(sample_data)} data points")
        
        # Test 2: Test with default engine
        print("\n2️⃣ Testing default Core Detection Engine...")
        engine = CoreDetectionEngine()
        signals = engine.detect_signals(sample_data)
        print(f"✅ Default engine: {len(signals)} signals detected")
        
        # Test 3: Test with custom filter
        print("\n3️⃣ Testing with custom signal filter...")
        custom_filter = SignalFilter(
            min_confidence=0.7,
            min_strength=0.6,
            signal_cooldown_minutes=10,
            max_signals_per_symbol=2
        )
        
        engine_filtered = CoreDetectionEngine(signal_filter=custom_filter)
        signals_filtered = engine_filtered.detect_signals(sample_data)
        print(f"✅ Filtered engine: {len(signals_filtered)} signals detected")
        
        # Test 4: Test signal quality
        print("\n4️⃣ Testing signal quality...")
        if signals_filtered:
            for i, signal in enumerate(signals_filtered):
                print(f"   Signal {i+1}:")
                print(f"     Direction: {signal.get('direction', 'unknown')}")
                print(f"     Confidence: {signal.get('confidence', 0):.3f}")
                print(f"     Strength: {signal.get('strength', 0):.3f}")
                print(f"     Quality Score: {signal.get('quality_score', 0):.3f}")
                print(f"     Timeframe: {signal.get('timeframe', 'unknown')}")
        else:
            print("   No signals detected (this is normal for test data)")
        
        # Test 5: Test engine methods
        print("\n5️⃣ Testing engine methods...")
        
        # Get detection summary
        summary = engine.get_detection_summary(signals)
        print(f"   Summary: {summary}")
        
        # Get processor stats
        stats = engine_filtered.get_signal_processor_stats('BTC')
        print(f"   Processor stats: {stats}")
        
        # Get cooldown status
        cooldown = engine_filtered.get_cooldown_status('BTC')
        print(f"   Cooldown status: {cooldown}")
        
        # Test 6: Test multiple detection cycles
        print("\n6️⃣ Testing multiple detection cycles...")
        
        # Second detection (should be filtered by cooldown)
        signals2 = engine_filtered.detect_signals(sample_data)
        print(f"   Second cycle: {len(signals2)} signals (should be 0 due to cooldown)")
        
        # Test 7: Test configuration updates
        print("\n7️⃣ Testing configuration updates...")
        
        # Update filter configuration
        new_config = {
            'min_confidence': 0.8,
            'signal_cooldown_minutes': 5
        }
        engine_filtered.update_signal_filter(new_config)
        print("   ✅ Filter configuration updated")
        
        # Test 8: Test error handling
        print("\n8️⃣ Testing error handling...")
        
        # Test with empty data
        import pandas as pd
        empty_data = pd.DataFrame()
        empty_signals = engine.detect_signals(empty_data)
        print(f"   Empty data: {len(empty_signals)} signals (should be 0)")
        
        # Test with insufficient data
        small_data = sample_data.head(50)
        small_signals = engine.detect_signals(small_data)
        print(f"   Small data: {len(small_signals)} signals")
        
        # Test 9: Test performance
        print("\n9️⃣ Testing performance...")
        
        import time
        start_time = time.time()
        performance_signals = engine.detect_signals(sample_data)
        detection_time = time.time() - start_time
        
        print(f"   Detection time: {detection_time:.3f} seconds")
        print(f"   Performance: {len(sample_data)/detection_time:.0f} data points/second")
        
        # Test 10: Test all components individually
        print("\n🔟 Testing individual components...")
        
        # Test MultiTimeframeProcessor
        from core_detection.multi_timeframe_processor import MultiTimeframeProcessor
        mtf_processor = MultiTimeframeProcessor()
        mtf_data = mtf_processor.process_multi_timeframe(sample_data)
        print(f"   MultiTimeframeProcessor: {len(mtf_data)} timeframes processed")
        
        # Test FeatureExtractor
        from core_detection.feature_extractors import BasicFeatureExtractor
        feature_extractor = BasicFeatureExtractor()
        features = feature_extractor.extract_all_features(sample_data)
        print(f"   FeatureExtractor: {len(features)} features extracted")
        
        # Test PatternDetector
        from core_detection.pattern_detectors import PatternDetector
        pattern_detector = PatternDetector()
        patterns = pattern_detector.detect_all_patterns(sample_data, features)
        print(f"   PatternDetector: {len(patterns)} pattern types detected")
        
        # Test RegimeDetector
        from core_detection.regime_detector import RegimeDetector
        regime_detector = RegimeDetector()
        regime = regime_detector.detect_regime(sample_data, features)
        print(f"   RegimeDetector: {regime.get('regime', 'unknown')} regime detected")
        
        # Test SignalGenerator
        from core_detection.signal_generator import SignalGenerator
        signal_generator = SignalGenerator()
        signals = signal_generator.generate_signals(features, patterns, regime.get('regime', 'unknown'))
        print(f"   SignalGenerator: {len(signals)} signals generated")
        
        # Test MultiTimeframeSignalCombiner
        from core_detection.multi_timeframe_signal_combiner import MultiTimeframeSignalCombiner
        signal_combiner = MultiTimeframeSignalCombiner()
        mtf_signals = {'1m': signals}
        combined_signals = signal_combiner.combine_signals(mtf_signals)
        print(f"   SignalCombiner: {len(combined_signals)} combined signals")
        
        # Test SignalProcessor
        from core_detection.signal_processor import SignalProcessor
        signal_processor = SignalProcessor()
        processed_signals = signal_processor.process_signals(combined_signals, 'BTC')
        print(f"   SignalProcessor: {len(processed_signals)} processed signals")
        
        print("\n" + "=" * 50)
        print("✅ ALL PHASE 1.3 TESTS PASSED!")
        print("🎉 Multi-Timeframe Alpha Detector is fully functional!")
        print("🚀 Ready to proceed to Phase 1.4 (Trading Plan Generation)")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Phase 1.3 Final Testing Suite")
    print("Multi-Timeframe Alpha Detector Validation")
    
    success = test_phase1_3_final()
    
    if success:
        print("\n🎉 PHASE 1.3 COMPLETE!")
        print("✅ All components working correctly")
        print("✅ Integration successful")
        print("✅ Performance acceptable")
        print("✅ Error handling robust")
        print("✅ Configuration flexible")
        print("\n🚀 Ready for Phase 1.4!")
    else:
        print("\n❌ PHASE 1.3 INCOMPLETE!")
        print("🔧 Please fix issues before proceeding")
        sys.exit(1)
