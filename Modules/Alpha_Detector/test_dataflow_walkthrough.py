#!/usr/bin/env python3
"""
Dataflow Walkthrough Test

This script walks through the complete dataflow from Raw Data Intelligence to CIL
to understand exactly what happens with the data at each step.

Flow:
1. Raw Data Intelligence processes market data every 5 minutes
2. Creates individual pattern strands + compilation strand (RMC)
3. CIL receives and processes these strands
4. CIL creates strategic insights and meta-signals
5. Other agents receive CIL insights
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def __init__(self):
        self.client = MockSupabaseClient()
        self.strands = []  # Store strands in memory
    
    def insert_strand(self, strand):
        """Insert a strand"""
        self.strands.append(strand)
        logger.info(f"Inserted strand: {strand['id']}")
        return {'data': [strand]}
    
    def execute_query(self, query, params=None):
        """Execute a query"""
        # Mock query execution
        return []


class MockSupabaseClient:
    """Mock Supabase client"""
    
    def table(self, table_name):
        return MockTable()


class MockTable:
    """Mock table"""
    
    def select(self, columns):
        return self
    
    def gte(self, column, value):
        return self
    
    def order(self, column, desc=False):
        return self
    
    def limit(self, count):
        return self
    
    def execute(self):
        return MockResult()


class MockResult:
    """Mock result"""
    
    def __init__(self):
        self.data = []


class MockOpenRouterClient:
    """Mock OpenRouter client"""
    
    def __init__(self):
        pass


async def test_raw_data_intelligence_flow():
    """Test the raw data intelligence flow"""
    print("\n=== STEP 1: Raw Data Intelligence Processing ===")
    
    # Initialize raw data intelligence agent
    supabase_manager = MockSupabaseManager()
    llm_client = MockOpenRouterClient()
    
    agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
    
    # Create mock market data
    mock_data = create_mock_market_data()
    print(f"Created mock market data: {len(mock_data)} rows")
    
    # Simulate the analysis process
    print("Running raw data analysis...")
    analysis_results = await agent._analyze_raw_data_enhanced(mock_data)
    
    print(f"Analysis results keys: {list(analysis_results.keys())}")
    print(f"Significant patterns found: {len(analysis_results.get('significant_patterns', []))}")
    
    # Simulate publishing findings
    print("Publishing findings...")
    await agent._publish_findings(analysis_results)
    
    print(f"Total strands created: {len(supabase_manager.strands)}")
    
    # Show the strands created
    for i, strand in enumerate(supabase_manager.strands):
        print(f"\nStrand {i+1}:")
        print(f"  ID: {strand['id']}")
        print(f"  Kind: {strand['kind']}")
        print(f"  Agent ID: {strand['agent_id']}")
        print(f"  Team Member: {strand['team_member']}")
        print(f"  Symbol: {strand['symbol']}")
        print(f"  Tags: {strand['tags']}")
        print(f"  Pattern Type: {strand.get('module_intelligence', {}).get('pattern_type', 'N/A')}")
    
    return supabase_manager.strands


def create_mock_market_data():
    """Create mock market data for testing"""
    # Create 240 minutes of 1-minute data (4 hours)
    timestamps = pd.date_range(
        start=datetime.now(timezone.utc) - timedelta(hours=4),
        end=datetime.now(timezone.utc),
        freq='1min'
    )
    
    # Generate realistic OHLCV data
    np.random.seed(42)  # For reproducible results
    
    # Start with base price
    base_price = 50000
    prices = [base_price]
    
    # Generate price movements
    for i in range(1, len(timestamps)):
        # Random walk with slight upward bias
        change = np.random.normal(0.001, 0.02)  # 0.1% mean, 2% std
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1000))  # Minimum price of 1000
    
    # Create OHLCV data
    data = []
    for i, timestamp in enumerate(timestamps):
        price = prices[i]
        
        # Generate OHLC from price
        high = price * (1 + abs(np.random.normal(0, 0.005)))
        low = price * (1 - abs(np.random.normal(0, 0.005)))
        open_price = price * (1 + np.random.normal(0, 0.002))
        close = price
        
        # Generate volume (higher during certain periods)
        base_volume = 1000
        if i % 60 == 0:  # Every hour, create volume spike
            volume = base_volume * np.random.uniform(3, 8)
        else:
            volume = base_volume * np.random.uniform(0.5, 2)
        
        data.append({
            'timestamp': timestamp.isoformat(),
            'symbol': 'BTC',
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    return pd.DataFrame(data)


async def test_cil_processing_flow(strands):
    """Test how CIL processes the raw data intelligence strands"""
    print("\n=== STEP 2: CIL Processing ===")
    
    # Initialize CIL input processor
    supabase_manager = MockSupabaseManager()
    llm_client = MockOpenRouterClient()
    
    # Add the strands to our mock database
    supabase_manager.strands = strands
    
    input_processor = InputProcessor(supabase_manager, llm_client)
    
    print("Processing agent outputs...")
    agent_outputs = await input_processor.process_agent_outputs()
    
    print(f"Agent outputs processed: {len(agent_outputs)}")
    
    # Show what CIL extracted from each strand
    for i, output in enumerate(agent_outputs):
        print(f"\nAgent Output {i+1}:")
        print(f"  Agent ID: {output.agent_id}")
        print(f"  Detection Type: {output.detection_type}")
        print(f"  Confidence: {output.confidence}")
        print(f"  Signal Strength: {output.signal_strength}")
        print(f"  Context: {output.context}")
        print(f"  Performance Tags: {output.performance_tags}")
    
    print("\nProcessing cross-agent metadata...")
    cross_agent_metadata = await input_processor.process_cross_agent_metadata()
    
    print(f"Cross-agent metadata:")
    print(f"  Signal families: {cross_agent_metadata.signal_families}")
    print(f"  Coverage map entries: {len(cross_agent_metadata.coverage_map)}")
    print(f"  Confluence events: {len(cross_agent_metadata.confluence_events)}")
    
    return agent_outputs, cross_agent_metadata


async def test_cil_strategic_processing(agent_outputs, cross_agent_metadata):
    """Test how CIL creates strategic insights"""
    print("\n=== STEP 3: CIL Strategic Processing ===")
    
    # This would be where CIL creates strategic insights
    # For now, we'll simulate what would happen
    
    print("Analyzing patterns for strategic insights...")
    
    # Group by detection type
    detection_groups = {}
    for output in agent_outputs:
        detection_type = output.detection_type
        if detection_type not in detection_groups:
            detection_groups[detection_type] = []
        detection_groups[detection_type].append(output)
    
    print(f"Detection groups found: {list(detection_groups.keys())}")
    
    # Look for confluence events
    confluence_events = cross_agent_metadata.confluence_events
    print(f"Confluence events detected: {len(confluence_events)}")
    
    # Simulate strategic insights creation
    strategic_insights = []
    
    for detection_type, outputs in detection_groups.items():
        if len(outputs) > 1:  # Multiple detections of same type
            insight = {
                'type': 'confluence_event',
                'detection_type': detection_type,
                'count': len(outputs),
                'confidence': sum(o.confidence for o in outputs) / len(outputs),
                'signal_strength': sum(o.signal_strength for o in outputs) / len(outputs),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            strategic_insights.append(insight)
            print(f"  Created confluence insight: {detection_type} ({len(outputs)} detections)")
    
    print(f"Total strategic insights created: {len(strategic_insights)}")
    
    return strategic_insights


async def test_meta_signal_creation(strategic_insights):
    """Test how CIL creates meta-signals for other agents"""
    print("\n=== STEP 4: Meta-Signal Creation ===")
    
    # Simulate creating meta-signals
    meta_signals = []
    
    for insight in strategic_insights:
        if insight['type'] == 'confluence_event':
            meta_signal = {
                'id': f"cil_meta_{insight['detection_type']}_{int(datetime.now().timestamp())}",
                'kind': 'meta_signal',
                'agent_id': 'central_intelligence_layer',
                'team_member': 'cil_pattern_miner',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'tags': ['cil', 'meta_signal', 'confluence_event'],
                'content': {
                    'signal_type': 'confluence_event',
                    'detection_type': insight['detection_type'],
                    'count': insight['count'],
                    'confidence': insight['confidence'],
                    'signal_strength': insight['signal_strength'],
                    'message': f"Multiple {insight['detection_type']} detections detected across agents"
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            meta_signals.append(meta_signal)
            print(f"  Created meta-signal: {meta_signal['id']}")
    
    print(f"Total meta-signals created: {len(meta_signals)}")
    
    return meta_signals


async def test_agent_reception(meta_signals):
    """Test how other agents receive and process CIL meta-signals"""
    print("\n=== STEP 5: Agent Reception ===")
    
    # Simulate how other agents would receive these meta-signals
    for signal in meta_signals:
        print(f"Meta-signal {signal['id']} would be received by:")
        print(f"  - Raw Data Intelligence (for confluence awareness)")
        print(f"  - Indicator Intelligence (for pattern confirmation)")
        print(f"  - Decision Maker (for strategic context)")
        print(f"  - Trading agents (for execution context)")
        
        # Simulate processing
        print(f"  Processing: {signal['content']['message']}")
        print(f"  Action: Update analysis parameters based on confluence")
    
    print(f"\nTotal agents that would receive meta-signals: {len(meta_signals) * 4}")


async def main():
    """Run the complete dataflow walkthrough"""
    print("Starting Dataflow Walkthrough Test")
    print("=" * 60)
    
    try:
        # Step 1: Raw Data Intelligence
        strands = await test_raw_data_intelligence_flow()
        
        # Step 2: CIL Processing
        agent_outputs, cross_agent_metadata = await test_cil_processing_flow(strands)
        
        # Step 3: CIL Strategic Processing
        strategic_insights = await test_cil_strategic_processing(agent_outputs, cross_agent_metadata)
        
        # Step 4: Meta-Signal Creation
        meta_signals = await test_meta_signal_creation(strategic_insights)
        
        # Step 5: Agent Reception
        await test_agent_reception(meta_signals)
        
        print("\n" + "=" * 60)
        print("Dataflow Walkthrough Complete!")
        print("\nSummary:")
        print(f"✅ Raw Data Intelligence: {len(strands)} strands created")
        print(f"✅ CIL Processing: {len(agent_outputs)} agent outputs processed")
        print(f"✅ Strategic Insights: {len(strategic_insights)} insights created")
        print(f"✅ Meta-Signals: {len(meta_signals)} meta-signals created")
        print(f"✅ Agent Reception: {len(meta_signals) * 4} agent interactions simulated")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\nTest failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
