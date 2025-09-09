"""
Detailed Debug Test for Raw Data Intelligence

This test shows us exactly what the system is processing and why it makes the decisions it does.
We're not assuming it should generate signals - we just want to see the full pipeline.
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timezone, timedelta

from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

class TestRawDataIntelligenceDetailedDebug:
    """Detailed debug test for Raw Data Intelligence pipeline"""
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        # Create realistic market data
        timestamps = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(hours=2),
            end=datetime.now(timezone.utc),
            freq='1min'
        )
        
        # Generate realistic OHLCV data with some patterns
        np.random.seed(42)  # For reproducible results
        
        data = []
        base_price = 100.0
        
        for i, timestamp in enumerate(timestamps):
            # Create some price movement with volume spikes
            price_change = np.random.normal(0, 0.5)  # Small random changes
            
            # Add some volume spikes every 10 minutes
            if i % 10 == 0:
                volume_multiplier = np.random.uniform(2.0, 5.0)
            else:
                volume_multiplier = np.random.uniform(0.5, 1.5)
            
            base_price += price_change
            volume = int(np.random.uniform(1000, 5000) * volume_multiplier)
            
            data.append({
                'timestamp': timestamp.isoformat(),
                'symbol': 'BTC',
                'open': base_price,
                'high': base_price + abs(np.random.normal(0, 0.2)),
                'low': base_price - abs(np.random.normal(0, 0.2)),
                'close': base_price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_full_pipeline_debug(self, sample_market_data):
        """Test the full pipeline with detailed debugging"""
        print(f"\n🔍 FULL RAW DATA INTELLIGENCE PIPELINE DEBUG")
        print(f"📊 Input Data: {len(sample_market_data)} data points")
        print("="*80)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        
        try:
            # Step 1: Analyze raw data
            print("\n🎯 STEP 1: RAW DATA ANALYSIS")
            analysis_results = asyncio.run(agent._analyze_raw_data(sample_market_data))
            
            print(f"✅ Analysis completed at: {analysis_results.get('timestamp', 'unknown')}")
            print(f"📊 Analysis components processed: {len(analysis_results.get('analysis_components', {}))}")
            
            # Show detailed results for each component
            analysis_components = analysis_results.get('analysis_components', {})
            for component_name, component_result in analysis_components.items():
                print(f"\n📈 {component_name.upper()} COMPONENT:")
                if isinstance(component_result, dict):
                    print(f"   - Data Points: {component_result.get('data_points', 0)}")
                    print(f"   - Confidence: {component_result.get('confidence', 0.0):.3f}")
                    
                    # Show specific metrics for each component
                    if 'divergences_detected' in component_result:
                        print(f"   - Divergences Detected: {component_result.get('divergences_detected', 0)}")
                        if component_result.get('divergences_detected', 0) > 0:
                            print(f"   - Divergence Details: {len(component_result.get('divergence_details', []))} items")
                            # Show first few divergences
                            for i, div in enumerate(component_result.get('divergence_details', [])[:3]):
                                print(f"     {i+1}. {div.get('type', 'unknown')} - Strength: {div.get('strength', 0.0):.3f}")
                    
                    if 'volume_patterns' in component_result:
                        print(f"   - Volume Patterns: {len(component_result.get('volume_patterns', []))}")
                    
                    if 'patterns' in component_result:
                        print(f"   - Patterns: {len(component_result.get('patterns', []))}")
                    
                    if 'anomalies' in component_result:
                        print(f"   - Anomalies: {len(component_result.get('anomalies', []))}")
                    
                    if 'correlations' in component_result:
                        print(f"   - Correlations: {len(component_result.get('correlations', []))}")
                    
                    # Show any errors
                    if 'error' in component_result:
                        print(f"   ❌ Error: {component_result['error']}")
                else:
                    print(f"   - Result: {component_result}")
            
            # Step 2: Identify significant patterns
            print(f"\n🎯 STEP 2: SIGNIFICANT PATTERN IDENTIFICATION")
            significant_patterns = agent._identify_significant_patterns(analysis_results)
            
            print(f"📊 Significant Patterns Found: {len(significant_patterns)}")
            
            if significant_patterns:
                print("✅ Patterns identified:")
                for i, pattern in enumerate(significant_patterns):
                    print(f"   {i+1}. Type: {pattern.get('type', 'unknown')}")
                    print(f"      Severity: {pattern.get('severity', 'unknown')}")
                    print(f"      Confidence: {pattern.get('confidence', 0.0):.3f}")
                    if 'details' in pattern:
                        if isinstance(pattern['details'], list):
                            print(f"      Details: {len(pattern['details'])} items")
                        else:
                            print(f"      Details: {pattern['details']}")
            else:
                print("⚠️  No significant patterns identified")
            
            # Step 3: Check signal generation logic
            print(f"\n🎯 STEP 3: SIGNAL GENERATION LOGIC")
            
            # Check if patterns meet signal generation criteria
            signals = analysis_results.get('signals', [])
            print(f"📊 Signals Generated: {len(signals)}")
            
            if signals:
                print("✅ Signals generated:")
                for i, signal in enumerate(signals):
                    print(f"   {i+1}. Type: {signal.get('type', 'unknown')}")
                    print(f"      Confidence: {signal.get('confidence', 0.0):.3f}")
                    print(f"      Direction: {signal.get('direction', 'unknown')}")
            else:
                print("⚠️  No signals generated")
                
                # Debug why no signals were generated
                print("\n🔍 DEBUGGING SIGNAL GENERATION:")
                print("   Checking signal generation criteria...")
                
                # Check if we have significant patterns but no signals
                if significant_patterns:
                    print(f"   - Found {len(significant_patterns)} significant patterns")
                    print("   - Patterns should have been converted to signals")
                    print("   - Issue might be in signal conversion logic")
                else:
                    print("   - No significant patterns found")
                    print("   - This explains why no signals were generated")
                    
                    # Check individual component thresholds
                    print("\n   Component Analysis:")
                    for component_name, component_result in analysis_components.items():
                        if isinstance(component_result, dict):
                            divergences = component_result.get('divergences_detected', 0)
                            patterns = len(component_result.get('patterns', []))
                            volume_patterns = len(component_result.get('volume_patterns', []))
                            
                            if divergences > 0 or patterns > 0 or volume_patterns > 0:
                                print(f"   - {component_name}: Found {divergences} divergences, {patterns} patterns, {volume_patterns} volume patterns")
                                print(f"     This should have triggered pattern identification")
                            else:
                                print(f"   - {component_name}: No patterns found")
            
            # Step 4: Summary
            print(f"\n🎯 STEP 4: PIPELINE SUMMARY")
            print("="*80)
            print(f"📊 INPUT: {len(sample_market_data)} market data points")
            print(f"📊 ANALYSIS: {len(analysis_components)} components processed")
            print(f"📊 PATTERNS: {len(significant_patterns)} significant patterns identified")
            print(f"📊 SIGNALS: {len(signals)} signals generated")
            print("="*80)
            
            # Final assessment
            if len(signals) > 0:
                print("✅ PIPELINE WORKING: Signals generated successfully")
            elif len(significant_patterns) > 0:
                print("⚠️  PIPELINE PARTIAL: Patterns found but no signals generated")
                print("   - Issue likely in signal conversion logic")
            else:
                print("ℹ️  PIPELINE WORKING: No patterns found, no signals generated")
                print("   - This may be normal behavior for this data")
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            raise
    
    def test_signal_generation_thresholds(self, sample_market_data):
        """Test signal generation thresholds and criteria"""
        print(f"\n🔍 SIGNAL GENERATION THRESHOLDS DEBUG")
        print("="*80)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        
        try:
            # Get analysis results
            analysis_results = asyncio.run(agent._analyze_raw_data(sample_market_data))
            
            # Check each component's signal generation criteria
            analysis_components = analysis_results.get('analysis_components', {})
            
            print("📊 SIGNAL GENERATION CRITERIA CHECK:")
            
            for component_name, component_result in analysis_components.items():
                print(f"\n🔍 {component_name.upper()}:")
                
                if isinstance(component_result, dict):
                    # Check divergence criteria
                    divergences = component_result.get('divergences_detected', 0)
                    if divergences > 0:
                        print(f"   ✅ Divergences: {divergences} (threshold: > 0)")
                        print(f"      Should trigger signal generation")
                    else:
                        print(f"   ❌ Divergences: {divergences} (threshold: > 0)")
                    
                    # Check volume spike criteria
                    volume_spike = component_result.get('significant_volume_spike', False)
                    if volume_spike:
                        print(f"   ✅ Volume Spike: {volume_spike}")
                    else:
                        print(f"   ❌ Volume Spike: {volume_spike}")
                    
                    # Check anomaly criteria
                    anomalies = component_result.get('anomalies_detected', False)
                    if anomalies:
                        print(f"   ✅ Anomalies: {anomalies}")
                    else:
                        print(f"   ❌ Anomalies: {anomalies}")
                    
                    # Check pattern criteria
                    patterns = len(component_result.get('patterns', []))
                    if patterns > 0:
                        print(f"   ✅ Patterns: {patterns} (threshold: > 0)")
                    else:
                        print(f"   ❌ Patterns: {patterns} (threshold: > 0)")
                    
                    # Check confidence
                    confidence = component_result.get('confidence', 0.0)
                    print(f"   📊 Confidence: {confidence:.3f}")
                    
                else:
                    print(f"   ❌ Invalid result format: {type(component_result)}")
            
        except Exception as e:
            print(f"❌ Threshold test failed: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
