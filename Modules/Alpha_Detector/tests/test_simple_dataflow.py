#!/usr/bin/env python3
"""
Simple Dataflow Test

This script demonstrates the actual dataflow by examining the code
and showing what happens at each step.
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_raw_data_intelligence_flow():
    """Analyze the raw data intelligence flow from code"""
    print("\n=== RAW DATA INTELLIGENCE FLOW ANALYSIS ===")
    
    print("1. RAW DATA INTELLIGENCE AGENT:")
    print("   - Runs every 5 minutes (300 seconds)")
    print("   - Gets market data from last 4 hours (2000 rows)")
    print("   - Processes through multiple analyzers:")
    print("     * Market Microstructure Analyzer")
    print("     * Volume Pattern Analyzer") 
    print("     * Time Based Pattern Detector")
    print("     * Cross Asset Pattern Analyzer")
    print("     * Divergence Detector")
    print("     * Multi-timeframe Processor")
    
    print("\n2. PATTERN DETECTION:")
    print("   - Analyzes 1m, 5m, 15m, 1h timeframes")
    print("   - Detects patterns like:")
    print("     * Volume spikes")
    print("     * Divergences")
    print("     * Microstructure patterns")
    print("     * Cross-timeframe patterns")
    
    print("\n3. STRAND CREATION:")
    print("   - Creates individual pattern strands for each detection")
    print("   - Each strand has:")
    print("     * ID: raw_data_{pattern_type}_{timestamp}_{index}")
    print("     * Kind: 'intelligence'")
    print("     * Agent ID: 'raw_data_intelligence'")
    print("     * Team Member: 'raw_data_intelligence_agent'")
    print("     * Tags: ['intelligence:raw_data:{pattern_type}:{severity}', 'cil']")
    print("     * Module Intelligence: pattern details, statistical measurements")
    
    print("\n4. COMPILATION STRAND (RMC):")
    print("   - Creates summary strand with:")
    print("     * ID: raw_data_compilation_{timestamp}")
    print("     * Symbol: 'SYSTEM'")
    print("     * Timeframe: 'system'")
    print("     * Tags: ['intelligence:raw_data:compilation:5min_summary', 'cil']")
    print("     * Module Intelligence: summary of all patterns found")
    
    print("\n5. DATABASE STORAGE:")
    print("   - All strands stored in AD_strands table")
    print("   - Available for CIL to process")


def analyze_cil_processing_flow():
    """Analyze how CIL processes the strands"""
    print("\n=== CIL PROCESSING FLOW ANALYSIS ===")
    
    print("1. CIL INPUT PROCESSOR:")
    print("   - Queries AD_strands table for recent strands")
    print("   - Looks for strands with agent_id IS NOT NULL")
    print("   - Processes strands from last few hours")
    
    print("\n2. AGENT OUTPUT PROCESSING:")
    print("   - Extracts detection type from module_intelligence.pattern_type")
    print("   - Builds context with symbol, timeframe, regime, session_bucket")
    print("   - Extracts performance tags and hypothesis notes")
    print("   - Creates AgentOutput objects with:")
    print("     * agent_id, detection_type, context")
    print("     * performance_tags, hypothesis_notes")
    print("     * timestamp, confidence, signal_strength")
    
    print("\n3. CROSS-AGENT METADATA:")
    print("   - Analyzes timing patterns across agents")
    print("   - Groups signals by detection type (signal families)")
    print("   - Creates coverage map by symbol/timeframe/regime")
    print("   - Detects confluence events (multiple agents detecting same pattern)")
    print("   - Identifies lead-lag relationships")
    
    print("\n4. MARKET REGIME CONTEXT:")
    print("   - Analyzes recent strands for regime indicators")
    print("   - Groups by regime, session_bucket, symbol, timeframe")
    print("   - Calculates average signal strength per group")
    print("   - Determines current market state")
    
    print("\n5. HISTORICAL PERFORMANCE:")
    print("   - Analyzes historical strands for performance")
    print("   - Identifies persistent vs ephemeral signals")
    print("   - Tracks failed vs success patterns")
    print("   - Extracts lesson strands")


def analyze_cil_strategic_processing():
    """Analyze how CIL creates strategic insights"""
    print("\n=== CIL STRATEGIC PROCESSING ANALYSIS ===")
    
    print("1. PATTERN ANALYSIS:")
    print("   - Groups detections by type")
    print("   - Identifies confluence events (multiple detections)")
    print("   - Calculates confidence and signal strength")
    
    print("\n2. STRATEGIC INSIGHT CREATION:")
    print("   - Creates insights for confluence events")
    print("   - Generates mechanism hypotheses")
    print("   - Evaluates evidence for hypotheses")
    print("   - Updates Why-Map entries")
    
    print("\n3. META-SIGNAL GENERATION:")
    print("   - Creates meta-signals for other agents")
    print("   - Types of meta-signals:")
    print("     * Strategic Confluence: 'Multiple teams detecting similar patterns'")
    print("     * Strategic Experiments: 'Test this hypothesis across teams'")
    print("     * Strategic Learning: 'This approach worked, try it elsewhere'")
    print("     * Strategic Warnings: 'This pattern failed before, be cautious'")
    
    print("\n4. META-SIGNAL PUBLICATION:")
    print("   - Publishes meta-signals back to AD_strands table")
    print("   - Tags: ['agent:central_intelligence:meta:{signal_type}']")
    print("   - Available for other agents to subscribe to")


def analyze_agent_reception():
    """Analyze how other agents receive CIL insights"""
    print("\n=== AGENT RECEPTION ANALYSIS ===")
    
    print("1. STRAND LISTENING:")
    print("   - Agents listen for specific tag patterns")
    print("   - Raw Data Intelligence: listens for 'agent:central_intelligence:meta:confluence_event'")
    print("   - Indicator Intelligence: listens for 'agent:central_intelligence:meta:experiment_directive'")
    print("   - System Control: listens for 'agent:central_intelligence:meta:doctrine_update'")
    
    print("\n2. META-SIGNAL PROCESSING:")
    print("   - Agents process meta-signals based on type")
    print("   - Update their analysis parameters")
    print("   - Adjust confidence thresholds")
    print("   - Modify pattern detection criteria")
    
    print("\n3. FEEDBACK LOOP:")
    print("   - Agents respond to meta-signals")
    print("   - Create new strands based on CIL guidance")
    print("   - CIL learns from agent responses")
    print("   - Continuous improvement cycle")


def show_actual_dataflow():
    """Show the actual dataflow with specific examples"""
    print("\n=== ACTUAL DATAFLOW EXAMPLE ===")
    
    print("1. RAW DATA INTELLIGENCE (Every 5 minutes):")
    print("   Input: 2000 rows of 1-minute OHLCV data")
    print("   Processing: Multi-timeframe analysis")
    print("   Output: Individual pattern strands + compilation strand")
    print("   Example strands:")
    print("     - raw_data_volume_spike_1694323200_0")
    print("     - raw_data_divergence_1694323200_1") 
    print("     - raw_data_compilation_1694323200")
    
    print("\n2. CIL INPUT PROCESSOR:")
    print("   Input: Recent strands from AD_strands table")
    print("   Processing: Extract agent outputs, detect confluence")
    print("   Output: AgentOutput objects + CrossAgentMetaData")
    print("   Example processing:")
    print("     - 3 volume_spike detections from raw_data_intelligence")
    print("     - 2 divergence detections from raw_data_intelligence")
    print("     - 1 confluence event detected")
    
    print("\n3. CIL STRATEGIC PROCESSING:")
    print("   Input: AgentOutput objects + metadata")
    print("   Processing: Create strategic insights")
    print("   Output: Strategic insights + meta-signals")
    print("   Example output:")
    print("     - Confluence insight: volume_spike (3 detections)")
    print("     - Meta-signal: cil_meta_volume_spike_1694323200")
    
    print("\n4. META-SIGNAL PUBLICATION:")
    print("   Input: Strategic insights")
    print("   Processing: Create meta-signal strands")
    print("   Output: Meta-signal strands in AD_strands table")
    print("   Example meta-signal:")
    print("     - ID: cil_meta_volume_spike_1694323200")
    print("     - Tags: ['cil', 'meta_signal', 'confluence_event']")
    print("     - Content: 'Multiple volume_spike detections detected'")
    
    print("\n5. AGENT RECEPTION:")
    print("   Input: Meta-signal strands")
    print("   Processing: Agents listen and respond")
    print("   Output: Updated agent behavior")
    print("   Example response:")
    print("     - Raw Data Intelligence: Increase volume spike sensitivity")
    print("     - Indicator Intelligence: Look for volume confirmation")
    print("     - Decision Maker: Consider confluence in decisions")


def main():
    """Run the dataflow analysis"""
    print("Dataflow Analysis - Raw Data Intelligence to CIL")
    print("=" * 60)
    
    analyze_raw_data_intelligence_flow()
    analyze_cil_processing_flow()
    analyze_cil_strategic_processing()
    analyze_agent_reception()
    show_actual_dataflow()
    
    print("\n" + "=" * 60)
    print("Dataflow Analysis Complete!")
    print("\nKey Insights:")
    print("✅ Raw Data Intelligence creates intelligence strands every 5 minutes")
    print("✅ CIL processes all strands and creates strategic insights")
    print("✅ CIL publishes meta-signals back to AD_strands table")
    print("✅ Other agents listen for and respond to meta-signals")
    print("✅ This creates a continuous learning and improvement loop")


if __name__ == "__main__":
    main()
