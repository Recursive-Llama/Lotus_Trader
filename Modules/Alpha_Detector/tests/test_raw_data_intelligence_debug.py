"""
Debug test for Raw Data Intelligence components

This test will help us understand why Raw Data Intelligence is generating 0 signals
despite having market data available.
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timezone, timedelta

from src.intelligence.raw_data_intelligence.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.raw_data_intelligence.cross_asset_analyzer import CrossAssetPatternAnalyzer
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

class TestRawDataIntelligenceDebug:
    """Debug test for Raw Data Intelligence"""
    
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
    
    def test_divergence_detector_sync(self, sample_market_data):
        """Test divergence detector synchronously"""
        print(f"\n🔍 Testing Divergence Detector with {len(sample_market_data)} data points")
        
        detector = RawDataDivergenceDetector()
        
        # Test the method directly (not async)
        try:
            # Since the method is marked async but doesn't use await, we can call it directly
            result = asyncio.run(detector.analyze(sample_market_data))
            
            print(f"📊 Divergence Analysis Results:")
            print(f"   - Data Points: {result.get('data_points', 0)}")
            print(f"   - Divergences Detected: {result.get('divergences_detected', 0)}")
            print(f"   - Confidence: {result.get('confidence', 0.0)}")
            print(f"   - Patterns: {len(result.get('patterns', []))}")
            
            # Check if any divergences were detected
            if result.get('divergences_detected', 0) > 0:
                print("✅ Divergences detected!")
                for i, div in enumerate(result.get('divergence_details', [])[:3]):  # Show first 3
                    print(f"   Divergence {i+1}: {div.get('type', 'unknown')} - {div.get('strength', 0.0)}")
            else:
                print("⚠️  No divergences detected")
                
        except Exception as e:
            print(f"❌ Divergence detector failed: {e}")
            raise
    
    def test_volume_analyzer_sync(self, sample_market_data):
        """Test volume analyzer synchronously"""
        print(f"\n🔍 Testing Volume Analyzer with {len(sample_market_data)} data points")
        
        analyzer = VolumePatternAnalyzer()
        
        try:
            result = asyncio.run(analyzer.analyze(sample_market_data))
            
            print(f"📊 Volume Analysis Results:")
            print(f"   - Data Points: {result.get('data_points', 0)}")
            print(f"   - Volume Patterns: {len(result.get('volume_patterns', []))}")
            print(f"   - Anomalies: {len(result.get('anomalies', []))}")
            print(f"   - Confidence: {result.get('confidence', 0.0)}")
            
            # Check if any patterns were detected
            if result.get('volume_patterns', []):
                print("✅ Volume patterns detected!")
                for i, pattern in enumerate(result.get('volume_patterns', [])[:3]):  # Show first 3
                    print(f"   Pattern {i+1}: {pattern.get('type', 'unknown')} - {pattern.get('strength', 0.0)}")
            else:
                print("⚠️  No volume patterns detected")
                
        except Exception as e:
            print(f"❌ Volume analyzer failed: {e}")
            raise
    
    def test_cross_asset_analyzer_sync(self, sample_market_data):
        """Test cross-asset analyzer synchronously"""
        print(f"\n🔍 Testing Cross-Asset Analyzer with {len(sample_market_data)} data points")
        
        analyzer = CrossAssetPatternAnalyzer()
        
        try:
            result = asyncio.run(analyzer.analyze(sample_market_data))
            
            print(f"📊 Cross-Asset Analysis Results:")
            print(f"   - Data Points: {result.get('data_points', 0)}")
            print(f"   - Correlations: {len(result.get('correlations', []))}")
            print(f"   - Patterns: {len(result.get('patterns', []))}")
            print(f"   - Confidence: {result.get('confidence', 0.0)}")
            
            # Check if any patterns were detected
            if result.get('patterns', []):
                print("✅ Cross-asset patterns detected!")
                for i, pattern in enumerate(result.get('patterns', [])[:3]):  # Show first 3
                    print(f"   Pattern {i+1}: {pattern.get('type', 'unknown')} - {pattern.get('strength', 0.0)}")
            else:
                print("⚠️  No cross-asset patterns detected")
                
        except Exception as e:
            print(f"❌ Cross-asset analyzer failed: {e}")
            raise
    
    def test_raw_data_agent_integration(self, sample_market_data):
        """Test the full Raw Data Intelligence agent"""
        print(f"\n🔍 Testing Raw Data Intelligence Agent with {len(sample_market_data)} data points")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        
        try:
            # Test the analysis method directly
            result = asyncio.run(agent._analyze_raw_data(sample_market_data))
            
            print(f"📊 Raw Data Intelligence Agent Results:")
            print(f"   - Analysis Timestamp: {result.get('timestamp', 'unknown')}")
            print(f"   - Signals Generated: {len(result.get('signals', []))}")
            print(f"   - Analysis Components: {len(result.get('analysis_components', {}))}")
            
            # Show analysis component results
            analysis_components = result.get('analysis_components', {})
            for component, component_result in analysis_components.items():
                if isinstance(component_result, dict):
                    print(f"   - {component}: {component_result.get('data_points', 0)} data points")
                    if 'divergences_detected' in component_result:
                        print(f"     Divergences: {component_result.get('divergences_detected', 0)}")
                    if 'volume_patterns' in component_result:
                        print(f"     Volume Patterns: {len(component_result.get('volume_patterns', []))}")
                    if 'patterns' in component_result:
                        print(f"     Patterns: {len(component_result.get('patterns', []))}")
            
            # Check if any signals were generated
            signals = result.get('signals', [])
            if signals:
                print("✅ Signals generated!")
                for i, signal in enumerate(signals[:3]):  # Show first 3
                    print(f"   Signal {i+1}: {signal.get('type', 'unknown')} - {signal.get('confidence', 0.0)}")
            else:
                print("⚠️  No signals generated")
                
        except Exception as e:
            print(f"❌ Raw Data Intelligence agent failed: {e}")
            raise
    
    def test_market_data_format(self, sample_market_data):
        """Test if market data format is correct"""
        print(f"\n🔍 Testing Market Data Format")
        
        print(f"📊 Market Data Info:")
        print(f"   - Shape: {sample_market_data.shape}")
        print(f"   - Columns: {list(sample_market_data.columns)}")
        print(f"   - Data Types:")
        for col, dtype in sample_market_data.dtypes.items():
            print(f"     {col}: {dtype}")
        
        print(f"   - Sample Data:")
        print(sample_market_data.head(3).to_string())
        
        # Check for required columns
        required_columns = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in sample_market_data.columns]
        
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
        else:
            print("✅ All required columns present")
        
        # Check for null values
        null_counts = sample_market_data.isnull().sum()
        if null_counts.sum() > 0:
            print(f"⚠️  Null values found:")
            for col, count in null_counts.items():
                if count > 0:
                    print(f"     {col}: {count}")
        else:
            print("✅ No null values found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
