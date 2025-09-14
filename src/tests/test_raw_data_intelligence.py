#!/usr/bin/env python3
"""
Raw Data Intelligence Comprehensive Test

This test focuses on the raw data intelligence components in a realistic environment:
1. Individual Analyzer Testing
2. Agent Coordination Testing
3. Strand Creation Testing
4. Integration Testing
5. Performance Testing

This is a comprehensive test that validates the foundation layer of the system.
"""

import asyncio
import json
import logging
import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import random
import uuid

# Import Raw Data Intelligence components
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.raw_data_intelligence.market_microstructure import MarketMicrostructureAnalyzer
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.raw_data_intelligence.time_based_patterns import TimeBasedPatternDetector
from src.intelligence.raw_data_intelligence.cross_asset_analyzer import CrossAssetPatternAnalyzer
from src.intelligence.raw_data_intelligence.analyzers.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.team_coordination import TeamCoordination
from src.intelligence.raw_data_intelligence.llm_coordination import LLMCoordination
from src.intelligence.raw_data_intelligence.strand_creation import StrandCreation

# Import utilities
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RawDataIntelligenceTester:
    """Comprehensive test for Raw Data Intelligence system"""
    
    def __init__(self):
        self.supabase = SupabaseManager()
        self.llm_client = OpenRouterClient()
        
        # Initialize analyzers
        self.market_microstructure = MarketMicrostructureAnalyzer()
        self.volume_analyzer = VolumePatternAnalyzer()
        self.time_patterns = TimeBasedPatternDetector()
        self.cross_asset = CrossAssetPatternAnalyzer()
        self.divergence_detector = RawDataDivergenceDetector()
        
        # Initialize coordination components
        self.team_coordination = TeamCoordination()
        self.llm_coordination = LLMCoordination(self.llm_client)
        self.strand_creation = StrandCreation(self.supabase)
        
        # Initialize main agent
        self.raw_data_agent = RawDataIntelligenceAgent(self.supabase, self.llm_client)
        
        # Test results
        self.test_results = {}
        self.mock_data = {}
    
    async def run_comprehensive_test(self):
        """Run comprehensive raw data intelligence test"""
        logger.info("🚀 Starting Raw Data Intelligence Comprehensive Test")
        
        try:
            # 1. Create test data
            await self.create_test_data()
            
            # 2. Test individual analyzers
            await self.test_individual_analyzers()
            
            # 3. Test agent coordination
            await self.test_agent_coordination()
            
            # 4. Test strand creation
            await self.test_strand_creation()
            
            # 5. Test integration
            await self.test_integration()
            
            # 6. Test performance
            await self.test_performance()
            
            # 7. Generate report
            await self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Raw data intelligence test failed: {e}")
            raise
    
    async def create_test_data(self):
        """Create comprehensive test data"""
        logger.info("📊 Creating Test Data")
        
        # Clear existing test data
        await self.cleanup_test_data()
        
        # Create OHLCV data for multiple assets and timeframes
        await self.create_ohlcv_data()
        
        # Create market scenarios
        await self.create_market_scenarios()
        
        # Create pattern examples
        await self.create_pattern_examples()
        
        logger.info("✅ Test data created")
    
    async def cleanup_test_data(self):
        """Clean up existing test data"""
        logger.info("  Cleaning up existing test data...")
        
        # Clean up test strands
        await self.supabase.execute_query(
            "DELETE FROM AD_strands WHERE tags->>'test_type' = 'raw_data_intelligence'"
        )
        
        logger.info("  Cleanup completed")
    
    async def create_ohlcv_data(self):
        """Create realistic OHLCV data"""
        logger.info("  Creating OHLCV data...")
        
        assets = ['BTC', 'ETH', 'SOL']
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        self.mock_data['ohlcv'] = {}
        
        for asset in assets:
            self.mock_data['ohlcv'][asset] = {}
            for timeframe in timeframes:
                # Create 1000 data points for each asset/timeframe
                data = self.generate_ohlcv_data(asset, timeframe, 1000)
                self.mock_data['ohlcv'][asset][timeframe] = data
        
        logger.info(f"  Created OHLCV data for {len(assets)} assets and {len(timeframes)} timeframes")
    
    def generate_ohlcv_data(self, asset: str, timeframe: str, count: int) -> pd.DataFrame:
        """Generate realistic OHLCV data"""
        # Base price for different assets
        base_prices = {'BTC': 50000, 'ETH': 3000, 'SOL': 100}
        base_price = base_prices.get(asset, 100)
        
        # Generate timestamps
        if timeframe == '1m':
            freq = '1min'
        elif timeframe == '5m':
            freq = '5min'
        elif timeframe == '15m':
            freq = '15min'
        elif timeframe == '1h':
            freq = '1H'
        elif timeframe == '4h':
            freq = '4H'
        else:  # 1d
            freq = '1D'
        
        timestamps = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(days=30),
            periods=count,
            freq=freq
        )
        
        # Generate price data with realistic movements
        np.random.seed(42)  # For reproducible results
        returns = np.random.normal(0, 0.02, count)  # 2% daily volatility
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Generate OHLCV data
        data = []
        for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
            # Generate realistic OHLC from price
            volatility = abs(np.random.normal(0, 0.01))
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            
            # Generate volume (higher during volatile periods)
            base_volume = 1000000
            volume_multiplier = 1 + volatility * 10
            volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 2.0))
            
            data.append({
                'timestamp': timestamp,
                'open': round(open_price, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'symbol': asset,  # Use 'symbol' instead of 'asset' for compatibility
                'asset': asset,
                'timeframe': timeframe
            })
        
        return pd.DataFrame(data)
    
    async def create_market_scenarios(self):
        """Create different market scenarios"""
        logger.info("  Creating market scenarios...")
        
        scenarios = {
            'bull_market': {'trend': 'up', 'volatility': 'normal'},
            'bear_market': {'trend': 'down', 'volatility': 'high'},
            'sideways': {'trend': 'flat', 'volatility': 'low'},
            'high_volatility': {'trend': 'mixed', 'volatility': 'very_high'},
            'low_volume': {'trend': 'flat', 'volatility': 'very_low'}
        }
        
        self.mock_data['scenarios'] = scenarios
        logger.info(f"  Created {len(scenarios)} market scenarios")
    
    async def create_pattern_examples(self):
        """Create pattern examples for testing"""
        logger.info("  Creating pattern examples...")
        
        patterns = {
            'volume_spikes': [],
            'divergences': [],
            'cross_asset_correlations': [],
            'time_patterns': [],
            'microstructure_anomalies': []
        }
        
        # Generate sample patterns
        for i in range(50):
            patterns['volume_spikes'].append({
                'id': f"volume_spike_{i}",
                'asset': random.choice(['BTC', 'ETH', 'SOL']),
                'timeframe': random.choice(['1h', '4h', '1d']),
                'volume_ratio': random.uniform(2.0, 5.0),
                'confidence': random.uniform(0.6, 0.9)
            })
            
            patterns['divergences'].append({
                'id': f"divergence_{i}",
                'asset': random.choice(['BTC', 'ETH', 'SOL']),
                'timeframe': random.choice(['1h', '4h', '1d']),
                'type': random.choice(['bullish', 'bearish']),
                'strength': random.uniform(0.5, 0.8)
            })
        
        self.mock_data['patterns'] = patterns
        logger.info(f"  Created pattern examples")
    
    async def test_individual_analyzers(self):
        """Test individual analyzers"""
        logger.info("🔍 Testing Individual Analyzers")
        
        start_time = time.time()
        
        try:
            # Test Market Microstructure Analyzer
            await self.test_market_microstructure()
            
            # Test Volume Pattern Analyzer
            await self.test_volume_analyzer()
            
            # Test Time-Based Pattern Detector
            await self.test_time_patterns()
            
            # Test Cross-Asset Analyzer
            await self.test_cross_asset_analyzer()
            
            # Test Divergence Detector
            await self.test_divergence_detector()
            
            duration = time.time() - start_time
            self.test_results['individual_analyzers'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info("✅ Individual analyzers tests passed")
            
        except Exception as e:
            logger.error(f"❌ Individual analyzers failed: {e}")
            self.test_results['individual_analyzers'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_market_microstructure(self):
        """Test Market Microstructure Analyzer"""
        logger.info("  Testing Market Microstructure Analyzer...")
        
        # Get test data
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test analysis
        result = await self.market_microstructure.analyze(btc_data)
        
        # Validate result
        assert 'timestamp' in result
        assert 'data_points' in result
        assert 'patterns' in result
        assert 'confidence' in result
        
        logger.info(f"    Analyzed {result['data_points']} data points")
        logger.info(f"    Found {len(result['patterns'])} patterns")
        logger.info(f"    Confidence: {result['confidence']:.2f}")
    
    async def test_volume_analyzer(self):
        """Test Volume Pattern Analyzer"""
        logger.info("  Testing Volume Pattern Analyzer...")
        
        # Get test data
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test analysis
        result = await self.volume_analyzer.analyze(btc_data)
        
        # Validate result
        assert 'timestamp' in result
        assert 'data_points' in result
        assert 'patterns' in result
        assert 'confidence' in result
        
        logger.info(f"    Analyzed {result['data_points']} data points")
        logger.info(f"    Found {len(result['patterns'])} patterns")
        logger.info(f"    Confidence: {result['confidence']:.2f}")
    
    async def test_time_patterns(self):
        """Test Time-Based Pattern Detector"""
        logger.info("  Testing Time-Based Pattern Detector...")
        
        # Get test data
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test analysis
        result = await self.time_patterns.analyze(btc_data)
        
        # Validate result
        assert 'timestamp' in result
        assert 'data_points' in result
        assert 'patterns' in result
        assert 'confidence' in result
        
        logger.info(f"    Analyzed {result['data_points']} data points")
        logger.info(f"    Found {len(result['patterns'])} patterns")
        logger.info(f"    Confidence: {result['confidence']:.2f}")
    
    async def test_cross_asset_analyzer(self):
        """Test Cross-Asset Analyzer"""
        logger.info("  Testing Cross-Asset Analyzer...")
        
        # Get test data for single asset (the analyzer expects a single DataFrame)
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test analysis
        result = await self.cross_asset.analyze(btc_data)
        
        # Validate result
        assert 'timestamp' in result
        assert 'data_points' in result
        assert 'patterns' in result
        assert 'confidence' in result
        
        logger.info(f"    Analyzed {result['data_points']} data points")
        logger.info(f"    Found {len(result['patterns'])} patterns")
        logger.info(f"    Confidence: {result['confidence']:.2f}")
    
    async def test_divergence_detector(self):
        """Test Divergence Detector"""
        logger.info("  Testing Divergence Detector...")
        
        # Get test data
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test analysis
        result = await self.divergence_detector.analyze(btc_data)
        
        # Validate result
        assert 'timestamp' in result
        assert 'data_points' in result
        assert 'patterns' in result
        assert 'confidence' in result
        
        logger.info(f"    Analyzed {result['data_points']} data points")
        logger.info(f"    Found {len(result['patterns'])} patterns")
        logger.info(f"    Confidence: {result['confidence']:.2f}")
    
    async def test_agent_coordination(self):
        """Test agent coordination"""
        logger.info("🤝 Testing Agent Coordination")
        
        start_time = time.time()
        
        try:
            # Test team coordination
            await self.test_team_coordination()
            
            # Test LLM coordination
            await self.test_llm_coordination()
            
            # Test main agent
            await self.test_raw_data_agent()
            
            duration = time.time() - start_time
            self.test_results['agent_coordination'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info("✅ Agent coordination tests passed")
            
        except Exception as e:
            logger.error(f"❌ Agent coordination failed: {e}")
            self.test_results['agent_coordination'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_team_coordination(self):
        """Test team coordination"""
        logger.info("  Testing Team Coordination...")
        
        # Get test data
        btc_data = self.mock_data['ohlcv']['BTC']['1m']
        
        # Create multi-timeframe data
        multi_timeframe_data = {
            '1m': self.mock_data['ohlcv']['BTC']['1m'],
            '5m': self.mock_data['ohlcv']['BTC']['5m'],
            '15m': self.mock_data['ohlcv']['BTC']['15m'],
            '1h': self.mock_data['ohlcv']['BTC']['1h']
        }
        
        # Test coordination
        try:
            result = await self.team_coordination.coordinate_team_analysis(btc_data, multi_timeframe_data)
            
            # Validate result
            assert 'microstructure' in result
            assert 'volume' in result
            assert 'time_patterns' in result
            assert 'cross_asset' in result
            assert 'divergences' in result  # Note: it's 'divergences', not 'divergence'
            
            logger.info(f"    Coordinated team analysis")
            logger.info(f"    Found {len(result)} analysis components")
        except Exception as e:
            logger.error(f"    Team coordination failed: {e}")
            # Check what we got
            logger.info(f"    Result keys: {list(result.keys()) if 'result' in locals() else 'No result'}")
            raise
    
    async def test_llm_coordination(self):
        """Test LLM coordination"""
        logger.info("  Testing LLM Coordination...")
        
        # Create team analysis data
        team_analysis = {
            'microstructure': {'patterns': [], 'confidence': 0.7},
            'volume': {'patterns': [], 'confidence': 0.8}
        }
        
        analysis_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_patterns': 0,
            'confidence': 0.75
        }
        
        market_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test LLM coordination
        try:
            result = self.llm_coordination.perform_llm_coordination(team_analysis, analysis_results, market_data)
            
            # Validate result
            assert 'coordinated_insights' in result, f"Missing 'coordinated_insights' in result: {list(result.keys())}"
            assert 'meta_analysis' in result, f"Missing 'meta_analysis' in result: {list(result.keys())}"
            assert 'overall_confidence' in result, f"Missing 'overall_confidence' in result: {list(result.keys())}"
            
            logger.info(f"    Performed LLM coordination")
            logger.info(f"    Overall confidence: {result['overall_confidence']:.2f}")
        except Exception as e:
            logger.error(f"    LLM coordination failed: {e}")
            logger.info(f"    Result keys: {list(result.keys()) if 'result' in locals() else 'No result'}")
            raise
    
    async def test_raw_data_agent(self):
        """Test main raw data agent"""
        logger.info("  Testing Raw Data Agent...")
        
        # Test agent initialization
        assert self.raw_data_agent.agent_name == "raw_data_intelligence"
        assert self.raw_data_agent.supabase_manager is not None
        assert self.raw_data_agent.llm_client is not None
        
        # Test agent properties
        assert hasattr(self.raw_data_agent, 'context_system')
        assert hasattr(self.raw_data_agent, 'prompt_manager')
        
        logger.info(f"    Agent name: {self.raw_data_agent.agent_name}")
        logger.info(f"    Agent has context system: {hasattr(self.raw_data_agent, 'context_system')}")
        logger.info(f"    Agent has prompt manager: {hasattr(self.raw_data_agent, 'prompt_manager')}")
    
    async def test_strand_creation(self):
        """Test strand creation"""
        logger.info("📝 Testing Strand Creation")
        
        start_time = time.time()
        
        try:
            # Test pattern strand creation
            await self.test_pattern_strand_creation()
            
            # Test overview strand creation
            await self.test_overview_strand_creation()
            
            duration = time.time() - start_time
            self.test_results['strand_creation'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info("✅ Strand creation tests passed")
            
        except Exception as e:
            logger.error(f"❌ Strand creation failed: {e}")
            self.test_results['strand_creation'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_pattern_strand_creation(self):
        """Test pattern strand creation"""
        logger.info("  Testing Pattern Strand Creation...")
        
        # Create sample analysis data
        analyzer_name = "volume_analyzer"
        analysis = {
            'patterns': [{'type': 'volume_spike', 'confidence': 0.8}],
            'confidence': 0.8
        }
        analysis_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_patterns': 1,
            'confidence': 0.8
        }
        market_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test strand creation
        strand_id = await self.strand_creation.create_individual_analyzer_strand(
            analyzer_name, analysis, analysis_results, market_data
        )
        
        # Validate result
        assert strand_id is not None
        assert isinstance(strand_id, str)
        
        logger.info(f"    Created pattern strand: {strand_id}")
    
    async def test_overview_strand_creation(self):
        """Test overview strand creation"""
        logger.info("  Testing Overview Strand Creation...")
        
        # Create sample team analysis
        team_analysis = {
            'microstructure': {'patterns': [], 'confidence': 0.7},
            'volume': {'patterns': [], 'confidence': 0.8}
        }
        
        # Create individual strand IDs
        individual_strand_ids = [f"strand_{i}" for i in range(3)]
        
        # Create analysis results
        analysis_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_patterns': 0,
            'confidence': 0.75
        }
        
        # Create meta analysis
        meta_analysis = {
            'meta_confidence': 0.75,
            'insights': ['No significant patterns detected'],
            'recommendations': ['Continue monitoring']
        }
        
        # Create CIL recommendations
        cil_recommendations = [
            {'type': 'monitor', 'priority': 'medium', 'description': 'Continue monitoring for patterns'}
        ]
        
        # Create market data
        market_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test overview strand creation
        strand_id = await self.strand_creation.create_overview_strand_with_llm_results(
            individual_strand_ids, team_analysis, meta_analysis, cil_recommendations, analysis_results, market_data
        )
        
        # Validate result
        assert strand_id is not None
        assert isinstance(strand_id, str)
        
        logger.info(f"    Created overview strand: {strand_id}")
    
    async def test_integration(self):
        """Test integration between components"""
        logger.info("🔗 Testing Integration")
        
        start_time = time.time()
        
        try:
            # Test data flow through system
            await self.test_data_flow()
            
            # Test pattern detection pipeline
            await self.test_pattern_detection_pipeline()
            
            # Test CIL integration
            await self.test_cil_integration()
            
            duration = time.time() - start_time
            self.test_results['integration'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info("✅ Integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Integration failed: {e}")
            logger.error(f"❌ Integration error type: {type(e)}")
            logger.error(f"❌ Integration error args: {e.args}")
            import traceback
            logger.error(f"❌ Integration traceback: {traceback.format_exc()}")
            self.test_results['integration'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_data_flow(self):
        """Test data flow through system"""
        logger.info("  Testing Data Flow...")
        
        # Test OHLCV data processing
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Process through analyzers
        results = []
        analyzers = [
            self.market_microstructure,
            self.volume_analyzer,
            self.time_patterns
        ]
        
        for analyzer in analyzers:
            result = await analyzer.analyze(btc_data)
            results.append(result)
        
        # Validate results
        assert len(results) == len(analyzers)
        for result in results:
            assert 'patterns' in result
            assert 'confidence' in result
        
        logger.info(f"    Processed data through {len(analyzers)} analyzers")
        logger.info(f"    Total patterns found: {sum(len(r['patterns']) for r in results)}")
    
    async def test_pattern_detection_pipeline(self):
        """Test pattern detection pipeline"""
        logger.info("  Testing Pattern Detection Pipeline...")
        
        # Test complete pipeline
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Run through main agent's analysis method
        result = await self.raw_data_agent._analyze_raw_data(btc_data)
        
        # Validate result
        assert 'timestamp' in result
        assert 'data_points' in result
        assert 'asset_results' in result
        assert 'total_patterns' in result
        
        logger.info(f"    Pipeline processed {result['data_points']} data points")
        logger.info(f"    Found {result['total_patterns']} total patterns")
        logger.info(f"    Processed {result['asset_count']} assets")
    
    async def test_cil_integration(self):
        """Test CIL integration"""
        logger.info("  Testing CIL Integration...")
        
        # Test pattern delivery to CIL by creating individual analyzer strands
        analyzer_name = "volume_analyzer"
        analysis = {
            'patterns': [{'type': 'volume_spike', 'confidence': 0.8}],
            'confidence': 0.8
        }
        analysis_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_patterns': 1,
            'confidence': 0.8
        }
        market_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Create pattern strand
        strand_id = await self.strand_creation.create_individual_analyzer_strand(
            analyzer_name, analysis, analysis_results, market_data
        )
        
        # Validate strand was created
        assert strand_id is not None
        assert isinstance(strand_id, str)
        
        logger.info(f"    Created pattern strand for CIL: {strand_id}")
    
    async def test_performance(self):
        """Test performance"""
        logger.info("⚡ Testing Performance")
        
        start_time = time.time()
        
        try:
            # Test analyzer performance
            await self.test_analyzer_performance()
            
            # Test memory usage
            await self.test_memory_usage()
            
            # Test scalability
            await self.test_scalability()
            
            duration = time.time() - start_time
            self.test_results['performance'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info("✅ Performance tests passed")
            
        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            self.test_results['performance'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_analyzer_performance(self):
        """Test analyzer performance"""
        logger.info("  Testing Analyzer Performance...")
        
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        
        # Test each analyzer
        analyzers = [
            ('Market Microstructure', self.market_microstructure),
            ('Volume Analyzer', self.volume_analyzer),
            ('Time Patterns', self.time_patterns),
            ('Cross Asset', self.cross_asset),
            ('Divergence Detector', self.divergence_detector)
        ]
        
        performance_results = {}
        
        for name, analyzer in analyzers:
            start_time = time.time()
            result = await analyzer.analyze(btc_data)
            duration = time.time() - start_time
            
            performance_results[name] = {
                'duration': duration,
                'patterns_found': len(result['patterns']),
                'confidence': result['confidence']
            }
            
            logger.info(f"    {name}: {duration:.3f}s, {len(result['patterns'])} patterns")
        
        # Validate performance (should be under 2 seconds each)
        for name, perf in performance_results.items():
            assert perf['duration'] < 2.0, f"{name} took too long: {perf['duration']:.3f}s"
    
    async def test_memory_usage(self):
        """Test memory usage"""
        logger.info("  Testing Memory Usage...")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        btc_data = self.mock_data['ohlcv']['BTC']['1h']
        results = []
        
        for _ in range(10):  # Process 10 times
            result = await self.market_microstructure.analyze(btc_data)
            results.append(result)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        logger.info(f"    Initial memory: {initial_memory:.1f} MB")
        logger.info(f"    Final memory: {final_memory:.1f} MB")
        logger.info(f"    Memory increase: {memory_increase:.1f} MB")
        
        # Validate memory usage (should be under 100MB increase)
        assert memory_increase < 100, f"Memory usage too high: {memory_increase:.1f} MB"
    
    async def test_scalability(self):
        """Test scalability"""
        logger.info("  Testing Scalability...")
        
        # Test with multiple assets
        assets = ['BTC', 'ETH', 'SOL']
        results = []
        
        start_time = time.time()
        
        for asset in assets:
            data = self.mock_data['ohlcv'][asset]['1h']
            result = await self.volume_analyzer.analyze(data)
            results.append(result)
        
        duration = time.time() - start_time
        
        logger.info(f"    Processed {len(assets)} assets in {duration:.3f}s")
        logger.info(f"    Average per asset: {duration/len(assets):.3f}s")
        
        # Validate scalability (should scale linearly)
        assert duration < 5.0, f"Scalability test took too long: {duration:.3f}s"
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("📊 Generating Test Report")
        
        # Calculate overall statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASSED')
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Calculate total duration
        total_duration = sum(result.get('duration', 0) for result in self.test_results.values())
        
        # Generate report
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': success_rate,
                'total_duration': total_duration
            },
            'test_results': self.test_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Save report
        with open('raw_data_intelligence_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info("📋 RAW DATA INTELLIGENCE TEST REPORT")
        logger.info("=" * 50)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed Tests: {passed_tests}")
        logger.info(f"Failed Tests: {failed_tests}")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        for test_name, result in self.test_results.items():
            status = "✅" if result['status'] == 'PASSED' else "❌"
            duration = result.get('duration', 0)
            logger.info(f"  {test_name}: {status} ({duration:.2f}s)")
        
        if success_rate == 100:
            logger.info("🎉 ALL RAW DATA INTELLIGENCE TESTS PASSED! System is working correctly!")
        else:
            logger.error(f"❌ {failed_tests} tests failed. System needs attention.")
        
        logger.info("📄 Test report saved to raw_data_intelligence_test_report.json")

async def main():
    """Main test execution"""
    tester = RawDataIntelligenceTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
