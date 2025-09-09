"""
Pattern Dataflow Test

This test tracks the complete pattern dataflow:
1. Pattern Detection in Raw Data Intelligence
2. Pattern Transmission to CIL
3. CIL Processing of Patterns

We're not looking for signals - we're tracking the pattern management system.
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timezone, timedelta

from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

class TestPatternDataflow:
    """Test the complete pattern dataflow from detection to CIL processing"""
    
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
    
    def test_pattern_detection_flow(self, sample_market_data):
        """Test pattern detection in Raw Data Intelligence"""
        print(f"\n🔍 STEP 1: PATTERN DETECTION IN RAW DATA INTELLIGENCE")
        print("="*80)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        
        try:
            # Analyze raw data
            analysis_results = asyncio.run(agent._analyze_raw_data(sample_market_data))
            
            print(f"📊 Analysis Results:")
            print(f"   - Data Points: {analysis_results.get('data_points', 0)}")
            print(f"   - Analysis Timestamp: {analysis_results.get('timestamp', 'unknown')}")
            
            # Check analysis components
            analysis_components = analysis_results.get('analysis_components', {})
            print(f"   - Components Processed: {len(analysis_components)}")
            
            total_patterns = 0
            total_divergences = 0
            
            for component_name, component_result in analysis_components.items():
                if isinstance(component_result, dict):
                    patterns = len(component_result.get('patterns', []))
                    divergences = component_result.get('divergences_detected', 0)
                    volume_patterns = len(component_result.get('volume_patterns', []))
                    anomalies = len(component_result.get('anomalies', []))
                    
                    total_patterns += patterns + volume_patterns + anomalies
                    total_divergences += divergences
                    
                    print(f"   - {component_name}: {patterns} patterns, {divergences} divergences, {volume_patterns} volume patterns, {anomalies} anomalies")
            
            print(f"\n📈 PATTERN DETECTION SUMMARY:")
            print(f"   - Total Patterns Found: {total_patterns}")
            print(f"   - Total Divergences Found: {total_divergences}")
            
            # Check significant patterns
            significant_patterns = analysis_results.get('significant_patterns', [])
            print(f"   - Significant Patterns: {len(significant_patterns)}")
            
            if significant_patterns:
                print("   ✅ Significant patterns identified:")
                for i, pattern in enumerate(significant_patterns):
                    print(f"      {i+1}. {pattern.get('type', 'unknown')} - {pattern.get('severity', 'unknown')} - {pattern.get('confidence', 0.0):.3f}")
            else:
                print("   ⚠️  No significant patterns identified")
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ Pattern detection failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_pattern_transmission_flow(self, sample_market_data):
        """Test pattern transmission from Raw Data Intelligence to database"""
        print(f"\n🔍 STEP 2: PATTERN TRANSMISSION TO DATABASE")
        print("="*80)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        
        try:
            # Get initial strand count
            initial_strands = supabase_manager.get_recent_strands(days=1)
            initial_count = len(initial_strands) if initial_strands else 0
            print(f"📊 Initial strands in database: {initial_count}")
            
            # Analyze raw data (this should trigger pattern publishing)
            analysis_results = await agent._analyze_raw_data(sample_market_data)
            
            # Check if significant patterns were found
            significant_patterns = analysis_results.get('significant_patterns', [])
            print(f"📊 Significant patterns found: {len(significant_patterns)}")
            
            if significant_patterns:
                # Manually trigger publishing (since the test doesn't run the full loop)
                await agent._publish_findings(analysis_results)
                print("✅ Published findings to database")
                
                # Check if strands were added
                final_strands = supabase_manager.get_recent_strands(days=1)
                final_count = len(final_strands) if final_strands else 0
                new_strands = final_count - initial_count
                
                print(f"📊 New strands added: {new_strands}")
                
                if new_strands > 0:
                    print("✅ Patterns successfully transmitted to database")
                    
                    # Show the new strands
                    recent_strands = final_strands[-new_strands:] if new_strands > 0 else []
                    for i, strand in enumerate(recent_strands):
                        print(f"   Strand {i+1}: {strand.get('kind', 'unknown')} - {strand.get('agent_id', 'unknown')}")
                else:
                    print("⚠️  No new strands added to database")
            else:
                print("ℹ️  No significant patterns to transmit")
            
        except Exception as e:
            print(f"❌ Pattern transmission failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_cil_pattern_processing(self, sample_market_data):
        """Test CIL processing of patterns from database"""
        print(f"\n🔍 STEP 3: CIL PATTERN PROCESSING")
        print("="*80)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        input_processor = InputProcessor(supabase_manager, llm_client)
        
        try:
            # First, ensure we have some patterns in the database
            analysis_results = await agent._analyze_raw_data(sample_market_data)
            significant_patterns = analysis_results.get('significant_patterns', [])
            
            if significant_patterns:
                await agent._publish_findings(analysis_results)
                print(f"✅ Published {len(significant_patterns)} patterns to database")
            
            # Now test CIL processing
            print(f"\n📊 CIL Input Processor Analysis:")
            
            # Process agent outputs (this reads from database)
            cil_outputs = await input_processor.process_agent_outputs()
            
            print(f"   - CIL Outputs Generated: {len(cil_outputs)}")
            
            if cil_outputs:
                print("   ✅ CIL successfully processed agent outputs:")
                for i, output in enumerate(cil_outputs):
                    print(f"      {i+1}. Agent: {output.agent_id} - Type: {output.detection_type} - Confidence: {output.confidence:.3f}")
                    
                    # Show context details
                    context = output.context
                    if 'pattern_type' in context:
                        print(f"         Pattern: {context['pattern_type']} - Severity: {context.get('severity', 'unknown')}")
                    if 'divergences_detected' in context:
                        print(f"         Divergences: {context['divergences_detected']}")
            else:
                print("   ⚠️  CIL found no agent outputs to process")
                
                # Debug: Check what's in the database
                recent_strands = supabase_manager.get_recent_strands(days=1)
                print(f"   📊 Recent strands in database: {len(recent_strands) if recent_strands else 0}")
                
                if recent_strands:
                    print("   Recent strand types:")
                    for strand in recent_strands[-5:]:  # Show last 5
                        print(f"      - {strand.get('kind', 'unknown')} from {strand.get('agent_id', 'unknown')}")
            
        except Exception as e:
            print(f"❌ CIL pattern processing failed: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_complete_pattern_dataflow(self, sample_market_data):
        """Test the complete pattern dataflow end-to-end"""
        print(f"\n🔍 COMPLETE PATTERN DATAFLOW TEST")
        print("="*80)
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        input_processor = InputProcessor(supabase_manager, llm_client)
        
        try:
            # Step 1: Pattern Detection
            print(f"\n🎯 STEP 1: PATTERN DETECTION")
            analysis_results = await agent._analyze_raw_data(sample_market_data)
            
            # Count patterns found
            analysis_components = analysis_results.get('analysis_components', {})
            total_patterns = 0
            total_divergences = 0
            
            for component_name, component_result in analysis_components.items():
                if isinstance(component_result, dict):
                    patterns = len(component_result.get('patterns', []))
                    divergences = component_result.get('divergences_detected', 0)
                    volume_patterns = len(component_result.get('volume_patterns', []))
                    anomalies = len(component_result.get('anomalies', []))
                    
                    total_patterns += patterns + volume_patterns + anomalies
                    total_divergences += divergences
            
            significant_patterns = analysis_results.get('significant_patterns', [])
            
            print(f"   📊 Patterns Detected: {total_patterns}")
            print(f"   📊 Divergences Detected: {total_divergences}")
            print(f"   📊 Significant Patterns: {len(significant_patterns)}")
            
            # Step 2: Pattern Transmission
            print(f"\n🎯 STEP 2: PATTERN TRANSMISSION")
            
            # Get initial strand count
            initial_strands = supabase_manager.get_recent_strands(days=1)
            initial_count = len(initial_strands) if initial_strands else 0
            
            if significant_patterns:
                await agent._publish_findings(analysis_results)
                
                # Check transmission
                final_strands = supabase_manager.get_recent_strands(days=1)
                final_count = len(final_strands) if final_strands else 0
                new_strands = final_count - initial_count
                
                print(f"   📊 Strands Transmitted: {new_strands}")
                print(f"   ✅ Transmission: {'Success' if new_strands > 0 else 'Failed'}")
            else:
                print(f"   ℹ️  No patterns to transmit")
            
            # Step 3: CIL Processing
            print(f"\n🎯 STEP 3: CIL PROCESSING")
            
            cil_outputs = await input_processor.process_agent_outputs()
            print(f"   📊 CIL Outputs: {len(cil_outputs)}")
            print(f"   ✅ CIL Processing: {'Success' if cil_outputs else 'No outputs to process'}")
            
            # Summary
            print(f"\n🎯 PATTERN DATAFLOW SUMMARY")
            print("="*80)
            print(f"📊 Detection: {total_patterns} patterns, {total_divergences} divergences")
            print(f"📊 Transmission: {len(significant_patterns)} significant patterns")
            print(f"📊 CIL Processing: {len(cil_outputs)} outputs")
            print("="*80)
            
            # Assessment
            if total_patterns > 0 and len(significant_patterns) > 0 and len(cil_outputs) > 0:
                print("✅ COMPLETE DATAFLOW WORKING: Patterns detected → transmitted → processed")
            elif total_patterns > 0 and len(significant_patterns) > 0:
                print("⚠️  PARTIAL DATAFLOW: Patterns detected and transmitted, but CIL not processing")
            elif total_patterns > 0:
                print("⚠️  PARTIAL DATAFLOW: Patterns detected but not transmitted")
            else:
                print("ℹ️  NO PATTERNS: This may be normal for this data")
            
        except Exception as e:
            print(f"❌ Complete dataflow test failed: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
