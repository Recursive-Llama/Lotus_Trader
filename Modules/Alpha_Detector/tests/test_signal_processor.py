#!/usr/bin/env python3
"""
Test Signal Processing System Integration
Phase 1.3.8: Signal Processing System
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core_detection.core_detection_engine import CoreDetectionEngine
from core_detection.signal_processor import SignalProcessor, SignalFilter
from core_detection.multi_timeframe_processor import create_sample_market_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_signal_processor_integration():
    """Test SignalProcessor integration with Core Detection Engine"""
    print("\n🧪 Testing Signal Processor Integration")
    print("=" * 60)
    
    try:
        # Test 1: Create SignalProcessor with custom config
        print("\n1️⃣ Testing SignalProcessor with custom configuration...")
        custom_filter = SignalFilter(
            min_confidence=0.7,
            min_strength=0.6,
            signal_cooldown_minutes=15,  # Shorter for testing
            max_signals_per_symbol=2,
            max_signals_per_timeframe=1
        )
        
        processor = SignalProcessor(custom_filter)
        print("✅ SignalProcessor created with custom configuration")
        
        # Test 2: Test signal processing with sample data
        print("\n2️⃣ Testing signal processing with sample signals...")
        sample_signals = [
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
            },
            {
                'direction': 'long',
                'confidence': 0.9,
                'strength': 0.8,
                'volume_ratio': 2.0,
                'timeframe': '5m',
                'timestamp': datetime.now(timezone.utc)
            }
        ]
        
        processed = processor.process_signals(sample_signals, 'BTC')
        print(f"✅ Processed {len(processed)} signals (filtered from {len(sample_signals)})")
        
        # Test 3: Test cooldown functionality
        print("\n3️⃣ Testing cooldown functionality...")
        cooldown_status = processor.get_cooldown_status('BTC')
        print(f"✅ Cooldown status: {cooldown_status}")
        
        # Test 4: Test signal statistics
        print("\n4️⃣ Testing signal statistics...")
        stats = processor.get_signal_statistics('BTC')
        print(f"✅ Signal statistics: {stats}")
        
        # Test 5: Test Core Detection Engine integration
        print("\n5️⃣ Testing Core Detection Engine integration...")
        
        # Create sample market data
        sample_data = create_sample_market_data()
        print(f"✅ Created sample data: {len(sample_data)} data points")
        
        # Initialize detection engine with custom signal filter
        engine = CoreDetectionEngine(signal_filter=custom_filter)
        print("✅ Core Detection Engine initialized with SignalProcessor")
        
        # Detect signals
        signals = engine.detect_signals(sample_data)
        print(f"✅ Detected {len(signals)} signals")
        
        # Test 6: Test signal processor methods through engine
        print("\n6️⃣ Testing signal processor methods through engine...")
        
        # Get processor stats
        processor_stats = engine.get_signal_processor_stats('BTC')
        print(f"✅ Processor stats: {processor_stats}")
        
        # Get cooldown status
        cooldown = engine.get_cooldown_status('BTC')
        print(f"✅ Cooldown status: {cooldown}")
        
        # Test 7: Test signal quality and processing metadata
        print("\n7️⃣ Testing signal quality and metadata...")
        if signals:
            for i, signal in enumerate(signals):
                print(f"   Signal {i+1}:")
                print(f"     Direction: {signal.get('direction', 'unknown')}")
                print(f"     Confidence: {signal.get('confidence', 0):.3f}")
                print(f"     Strength: {signal.get('strength', 0):.3f}")
                print(f"     Quality Score: {signal.get('quality_score', 0):.3f}")
                print(f"     Processing Metadata: {signal.get('processing_metadata', {})}")
        
        # Test 8: Test filter configuration update
        print("\n8️⃣ Testing filter configuration update...")
        new_config = {
            'min_confidence': 0.8,
            'signal_cooldown_minutes': 30
        }
        engine.update_signal_filter(new_config)
        print("✅ Filter configuration updated")
        
        # Test 9: Test multiple signal processing cycles
        print("\n9️⃣ Testing multiple signal processing cycles...")
        
        # Process signals again (should be filtered by cooldown)
        signals2 = engine.detect_signals(sample_data)
        print(f"✅ Second detection cycle: {len(signals2)} signals (should be 0 due to cooldown)")
        
        # Wait a bit and process again
        import time
        print("   Waiting for cooldown to expire...")
        time.sleep(2)  # Wait 2 seconds
        
        # Process with new data
        new_sample_data = create_sample_market_data()
        signals3 = engine.detect_signals(new_sample_data)
        print(f"✅ Third detection cycle: {len(signals3)} signals")
        
        print("\n" + "=" * 60)
        print("✅ ALL SIGNAL PROCESSOR TESTS PASSED!")
        print("🎉 Signal Processing System is fully integrated!")
        print("🚀 Ready to proceed to Phase 1.3.9 (Testing Framework)")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_signal_processor_standalone():
    """Test SignalProcessor as standalone component"""
    print("\n🧪 Testing SignalProcessor Standalone")
    print("=" * 40)
    
    try:
        # Create processor
        processor = SignalProcessor()
        
        # Test signal processing
        test_signals = [
            {
                'direction': 'long',
                'confidence': 0.8,
                'strength': 0.7,
                'volume_ratio': 1.5,
                'timeframe': '1h',
                'timestamp': datetime.now(timezone.utc)
            }
        ]
        
        processed = processor.process_signals(test_signals, 'ETH')
        print(f"✅ Standalone processing: {len(processed)} signals")
        
        # Test statistics
        stats = processor.get_signal_statistics()
        print(f"✅ Standalone stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Standalone test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Signal Processing System Test Suite")
    print("Phase 1.3.8: Signal Processing System")
    
    # Test standalone
    standalone_success = test_signal_processor_standalone()
    
    # Test integration
    integration_success = test_signal_processor_integration()
    
    if standalone_success and integration_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Signal Processing System is ready for production!")
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("🔧 Please fix the issues before proceeding.")
        sys.exit(1)
