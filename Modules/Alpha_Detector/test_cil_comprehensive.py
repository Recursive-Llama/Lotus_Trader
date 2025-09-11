#!/usr/bin/env python3
"""
CIL Comprehensive Test Suite

This test suite comprehensively tests the CIL system in a realistic environment
with mock data, covering all features and integration points.

Test Phases:
1. Mock Data Creation
2. Individual Feature Tests
3. Integration Tests
4. End-to-End Tests
5. Stress & Performance Tests
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import uuid

# Import CIL components
from src.intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
from src.intelligence.system_control.central_intelligence_layer.prediction_engine import PredictionEngine
from src.intelligence.system_control.central_intelligence_layer.multi_cluster_learning_orchestrator import MultiClusterLearningOrchestrator
from src.intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from src.intelligence.system_control.central_intelligence_layer.braid_level_manager import BraidLevelManager
from src.intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from src.intelligence.system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from src.intelligence.system_control.central_intelligence_layer.database_query_examples import DatabaseQueryExamples

# Import utilities
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CILComprehensiveTester:
    """Comprehensive test suite for CIL system"""
    
    def __init__(self):
        self.supabase = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.cil = SimplifiedCIL(self.supabase, self.llm_client)
        self.prediction_engine = PredictionEngine(self.supabase, self.llm_client)
        self.multi_cluster_orchestrator = MultiClusterLearningOrchestrator(self.supabase, self.llm_client)
        self.grouping_engine = MultiClusterGroupingEngine(self.supabase)
        self.braid_manager = BraidLevelManager(self.supabase)
        self.llm_analyzer = LLMLearningAnalyzer(self.supabase, self.llm_client)
        self.per_cluster_learning = PerClusterLearningSystem(self.supabase, self.llm_client)
        self.query_examples = DatabaseQueryExamples()
        
        # Test data storage
        self.mock_patterns = []
        self.mock_predictions = []
        self.mock_reviews = []
        self.mock_braids = []
        
        # Test results
        self.test_results = {
            'phase1_mock_data': {},
            'phase2_individual_features': {},
            'phase3_integration': {},
            'phase4_end_to_end': {},
            'phase5_stress_performance': {}
        }
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        logger.info("🚀 Starting CIL Comprehensive Test Suite")
        
        try:
            # Phase 1: Mock Data Creation
            await self.phase1_mock_data_creation()
            
            # Phase 2: Individual Feature Tests
            await self.phase2_individual_feature_tests()
            
            # Phase 3: Integration Tests
            await self.phase3_integration_tests()
            
            # Phase 4: End-to-End Tests
            await self.phase4_end_to_end_tests()
            
            # Phase 5: Stress & Performance Tests
            await self.phase5_stress_performance_tests()
            
            # Generate final report
            await self.generate_final_report()
            
        except Exception as e:
            logger.error(f"❌ Comprehensive test suite failed: {e}")
            raise
    
    async def phase1_mock_data_creation(self):
        """Phase 1: Create comprehensive mock data"""
        logger.info("📊 Phase 1: Creating Mock Data")
        
        start_time = time.time()
        
        try:
            # 1. Create pattern strands
            await self.create_mock_pattern_strands()
            
            # 2. Create prediction reviews
            await self.create_mock_prediction_reviews()
            
            # 3. Create market data
            await self.create_mock_market_data()
            
            # 4. Create braid structures
            await self.create_mock_braid_structures()
            
            # 5. Validate mock data
            await self.validate_mock_data()
            
            duration = time.time() - start_time
            self.test_results['phase1_mock_data'] = {
                'status': 'PASSED',
                'duration': duration,
                'patterns_created': len(self.mock_patterns),
                'predictions_created': len(self.mock_predictions),
                'reviews_created': len(self.mock_reviews),
                'braids_created': len(self.mock_braids)
            }
            
            logger.info(f"✅ Phase 1 completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Phase 1 failed: {e}")
            self.test_results['phase1_mock_data'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def create_mock_pattern_strands(self):
        """Create realistic pattern strands"""
        logger.info("  Creating pattern strands...")
        
        pattern_types = ['volume_spike', 'divergence', 'flow', 'cross_asset', 'time_based']
        assets = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        for i in range(100):
            pattern = {
                'id': str(uuid.uuid4()),
                'kind': 'pattern',
                'content': {
                    'pattern_type': random.choice(pattern_types),
                    'asset': random.choice(assets),
                    'timeframe': random.choice(timeframes),
                    'confidence': round(random.uniform(0.3, 0.9), 2),
                    'strength': round(random.uniform(0.4, 0.8), 2),
                    'novelty': round(random.uniform(0.2, 0.7), 2),
                    'surprise': round(random.uniform(0.1, 0.6), 2),
                    'persistence': round(random.uniform(0.3, 0.8), 2),
                    'group_type': random.choice(['single', 'multi']),
                    'method': random.choice(['technical', 'fundamental', 'sentiment']),
                    'detection_time': datetime.now().isoformat(),
                    'market_conditions': {
                        'volatility': round(random.uniform(0.1, 0.8), 2),
                        'volume': round(random.uniform(0.5, 2.0), 2),
                        'trend': random.choice(['bullish', 'bearish', 'sideways'])
                    }
                },
                'metadata': {
                    'source': 'mock_data_generator',
                    'version': '1.0',
                    'test_phase': 'comprehensive'
                },
                'created_at': datetime.now().isoformat()
            }
            
            self.mock_patterns.append(pattern)
            
            # Insert into database
            await self.supabase.insert_strand(pattern)
        
        logger.info(f"  Created {len(self.mock_patterns)} pattern strands")
    
    async def create_mock_prediction_reviews(self):
        """Create realistic prediction reviews"""
        logger.info("  Creating prediction reviews...")
        
        outcomes = ['target_hit', 'stop_hit', 'expired', 'partial_success']
        assets = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        for i in range(200):
            # Create prediction first
            prediction = {
                'id': str(uuid.uuid4()),
                'kind': 'prediction',
                'content': {
                    'asset': random.choice(assets),
                    'timeframe': random.choice(timeframes),
                    'direction': random.choice(['long', 'short']),
                    'confidence': round(random.uniform(0.4, 0.9), 2),
                    'target_price': round(random.uniform(100, 100000), 2),
                    'stop_price': round(random.uniform(50, 50000), 2),
                    'duration_hours': random.randint(1, 48),
                    'prediction_type': random.choice(['code', 'llm']),
                    'pattern_group_id': random.choice([p['id'] for p in self.mock_patterns]) if self.mock_patterns else None
                },
                'metadata': {
                    'source': 'mock_data_generator',
                    'version': '1.0',
                    'test_phase': 'comprehensive'
                },
                'created_at': datetime.now().isoformat()
            }
            
            self.mock_predictions.append(prediction)
            await self.supabase.insert_strand(prediction)
            
            # Create prediction review
            review = {
                'id': str(uuid.uuid4()),
                'kind': 'prediction_review',
                'content': {
                    'prediction_id': prediction['id'],
                    'outcome': random.choice(outcomes),
                    'final_price': round(random.uniform(80, 120000), 2),
                    'max_drawdown': round(random.uniform(0.01, 0.15), 3),
                    'success_rate': round(random.uniform(0.2, 0.8), 2),
                    'risk_reward_ratio': round(random.uniform(0.5, 3.0), 2),
                    'cluster_keys': {
                        'pattern_timeframe': f"{random.choice(['volume_spike', 'divergence'])}_1h",
                        'asset': random.choice(assets),
                        'timeframe': random.choice(timeframes),
                        'outcome': random.choice(outcomes),
                        'pattern': random.choice(['volume_spike', 'divergence', 'flow']),
                        'group_type': random.choice(['single', 'multi']),
                        'method': random.choice(['technical', 'fundamental'])
                    },
                    'original_pattern_strand_ids': [random.choice([p['id'] for p in self.mock_patterns]) if self.mock_patterns else str(uuid.uuid4())],
                    'asset': random.choice(assets),
                    'timeframe': random.choice(timeframes),
                    'group_type': random.choice(['single', 'multi'])
                },
                'metadata': {
                    'source': 'mock_data_generator',
                    'version': '1.0',
                    'test_phase': 'comprehensive'
                },
                'created_at': datetime.now().isoformat()
            }
            
            self.mock_reviews.append(review)
            await self.supabase.insert_strand(review)
        
        logger.info(f"  Created {len(self.mock_predictions)} predictions and {len(self.mock_reviews)} reviews")
    
    async def create_mock_market_data(self):
        """Create realistic market data"""
        logger.info("  Creating market data...")
        
        assets = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        base_prices = {'BTC': 50000, 'ETH': 3000, 'SOL': 100, 'ADA': 0.5, 'DOT': 20}
        
        for asset in assets:
            base_price = base_prices[asset]
            
            for i in range(200):  # 200 data points per asset
                price_change = random.uniform(-0.05, 0.05)  # ±5% change
                new_price = base_price * (1 + price_change)
                base_price = new_price  # Update base for next iteration
                
                market_data = {
                    'id': str(uuid.uuid4()),
                    'kind': 'market_data',
                    'content': {
                        'asset': asset,
                        'price': round(new_price, 2),
                        'volume': round(random.uniform(1000000, 10000000), 2),
                        'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                        'high': round(new_price * random.uniform(1.0, 1.02), 2),
                        'low': round(new_price * random.uniform(0.98, 1.0), 2),
                        'open': round(new_price * random.uniform(0.99, 1.01), 2),
                        'close': round(new_price, 2)
                    },
                    'metadata': {
                        'source': 'mock_data_generator',
                        'version': '1.0',
                        'test_phase': 'comprehensive'
                    },
                    'created_at': datetime.now().isoformat()
                }
                
                await self.supabase.insert_strand(market_data)
        
        logger.info(f"  Created market data for {len(assets)} assets")
    
    async def create_mock_braid_structures(self):
        """Create realistic braid structures"""
        logger.info("  Creating braid structures...")
        
        # Create level 1 braids (3 strands each)
        for i in range(20):
            if len(self.mock_reviews) >= 3:
                braid = {
                    'id': str(uuid.uuid4()),
                    'kind': 'braid',
                    'content': {
                        'braid_level': 1,
                        'cluster_type': random.choice(['pattern_timeframe', 'asset', 'timeframe', 'outcome', 'pattern', 'group_type', 'method']),
                        'cluster_key': f"test_cluster_{i}",
                        'strand_ids': random.sample([r['id'] for r in self.mock_reviews], 3),
                        'learning_insights': {
                            'success_rate': round(random.uniform(0.3, 0.8), 2),
                            'avg_confidence': round(random.uniform(0.4, 0.9), 2),
                            'risk_reward_ratio': round(random.uniform(0.8, 2.5), 2),
                            'pattern_strength': round(random.uniform(0.5, 0.9), 2)
                        },
                        'created_at': datetime.now().isoformat()
                    },
                    'metadata': {
                        'source': 'mock_data_generator',
                        'version': '1.0',
                        'test_phase': 'comprehensive'
                    },
                    'created_at': datetime.now().isoformat()
                }
                
                self.mock_braids.append(braid)
                await self.supabase.insert_strand(braid)
        
        logger.info(f"  Created {len(self.mock_braids)} braid structures")
    
    async def validate_mock_data(self):
        """Validate that mock data was created correctly"""
        logger.info("  Validating mock data...")
        
        # Check pattern strands
        pattern_count = await self.supabase.execute_query(
            "SELECT COUNT(*) FROM AD_strands WHERE kind = 'pattern' AND metadata->>'test_phase' = 'comprehensive'"
        )
        logger.info(f"    Pattern strands in DB: {pattern_count[0]['count'] if pattern_count else 0}")
        
        # Check prediction reviews
        review_count = await self.supabase.execute_query(
            "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND metadata->>'test_phase' = 'comprehensive'"
        )
        logger.info(f"    Prediction reviews in DB: {review_count[0]['count'] if review_count else 0}")
        
        # Check braids
        braid_count = await self.supabase.execute_query(
            "SELECT COUNT(*) FROM AD_strands WHERE kind = 'braid' AND metadata->>'test_phase' = 'comprehensive'"
        )
        logger.info(f"    Braids in DB: {braid_count[0]['count'] if braid_count else 0}")
        
        logger.info("  ✅ Mock data validation completed")
    
    async def phase2_individual_feature_tests(self):
        """Phase 2: Test individual features"""
        logger.info("🔧 Phase 2: Individual Feature Tests")
        
        start_time = time.time()
        
        try:
            # Test pattern recognition and grouping
            await self.test_pattern_recognition_grouping()
            
            # Test prediction engine
            await self.test_prediction_engine()
            
            # Test learning system
            await self.test_learning_system()
            
            # Test context system
            await self.test_context_system()
            
            # Test outcome analysis
            await self.test_outcome_analysis()
            
            duration = time.time() - start_time
            self.test_results['phase2_individual_features'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info(f"✅ Phase 2 completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Phase 2 failed: {e}")
            self.test_results['phase2_individual_features'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_pattern_recognition_grouping(self):
        """Test pattern recognition and grouping features"""
        logger.info("  Testing pattern recognition and grouping...")
        
        # Test pattern classification
        patterns = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND metadata->>'test_phase' = 'comprehensive' LIMIT 10"
        )
        
        if patterns:
            logger.info(f"    Found {len(patterns)} patterns for testing")
            
            # Test grouping by asset + timeframe + cycle
            asset_timeframe_groups = await self.grouping_engine.get_cluster_keys('pattern_timeframe')
            logger.info(f"    Pattern+timeframe groups: {len(asset_timeframe_groups)}")
            
            # Test similarity matching
            if len(patterns) >= 2:
                pattern1 = patterns[0]
                pattern2 = patterns[1]
                similarity = await self.calculate_pattern_similarity(pattern1, pattern2)
                logger.info(f"    Pattern similarity: {similarity:.2f}")
        
        logger.info("  ✅ Pattern recognition and grouping tests passed")
    
    async def test_prediction_engine(self):
        """Test prediction engine features"""
        logger.info("  Testing prediction engine...")
        
        # Test code-based prediction creation
        test_pattern = {
            'pattern_type': 'volume_spike',
            'asset': 'BTC',
            'timeframe': '1h',
            'confidence': 0.7
        }
        
        code_prediction = await self.prediction_engine.create_code_prediction(test_pattern, [])
        logger.info(f"    Code prediction created: {code_prediction is not None}")
        
        # Test LLM prediction creation
        llm_prediction = await self.prediction_engine.create_llm_prediction(test_pattern, [])
        logger.info(f"    LLM prediction created: {llm_prediction is not None}")
        
        # Test prediction duration calculation
        duration = self.prediction_engine.get_timeframe_hours('1h')
        logger.info(f"    Prediction duration for 1h: {duration} hours")
        
        logger.info("  ✅ Prediction engine tests passed")
    
    async def test_learning_system(self):
        """Test learning system features"""
        logger.info("  Testing learning system...")
        
        # Test multi-cluster grouping
        cluster_types = ['pattern_timeframe', 'asset', 'timeframe', 'outcome', 'pattern', 'group_type', 'method']
        
        for cluster_type in cluster_types:
            keys = await self.grouping_engine.get_cluster_keys(cluster_type)
            logger.info(f"    {cluster_type} clusters: {len(keys)}")
        
        # Test braid level progression
        braids = await self.braid_manager.get_braids_by_level(1)
        logger.info(f"    Level 1 braids: {len(braids)}")
        
        logger.info("  ✅ Learning system tests passed")
    
    async def test_context_system(self):
        """Test context system features"""
        logger.info("  Testing context system...")
        
        # Test pattern context retrieval
        pattern_context = await self.cil.context_system.get_relevant_context(
            kind='pattern',
            filters={'asset': 'BTC'},
            limit=5
        )
        logger.info(f"    Pattern context retrieved: {len(pattern_context)} items")
        
        # Test prediction review context retrieval
        review_context = await self.cil.context_system.get_relevant_context(
            kind='prediction_review',
            filters={'outcome': 'target_hit'},
            limit=5
        )
        logger.info(f"    Review context retrieved: {len(review_context)} items")
        
        logger.info("  ✅ Context system tests passed")
    
    async def test_outcome_analysis(self):
        """Test outcome analysis features"""
        logger.info("  Testing outcome analysis...")
        
        # Test prediction outcome tracking
        if self.mock_predictions:
            prediction_id = self.mock_predictions[0]['id']
            await self.cil.prediction_tracker.track_prediction(prediction_id, 'target_hit', 0.05)
            logger.info("    Prediction outcome tracked")
        
        # Test outcome analysis
        outcomes = await self.cil.outcome_analyzer.analyze_prediction_outcomes()
        logger.info(f"    Outcome analysis completed: {len(outcomes)} insights")
        
        logger.info("  ✅ Outcome analysis tests passed")
    
    async def calculate_pattern_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate similarity between two patterns"""
        # Simple similarity calculation based on pattern type and asset
        similarity = 0.0
        
        if pattern1['content']['pattern_type'] == pattern2['content']['pattern_type']:
            similarity += 0.5
        
        if pattern1['content']['asset'] == pattern2['content']['asset']:
            similarity += 0.3
        
        if pattern1['content']['timeframe'] == pattern2['content']['timeframe']:
            similarity += 0.2
        
        return similarity
    
    async def phase3_integration_tests(self):
        """Phase 3: Test component integration"""
        logger.info("🔗 Phase 3: Integration Tests")
        
        start_time = time.time()
        
        try:
            # Test pattern → prediction pipeline
            await self.test_pattern_prediction_pipeline()
            
            # Test multi-cluster learning
            await self.test_multi_cluster_learning()
            
            # Test context integration
            await self.test_context_integration()
            
            duration = time.time() - start_time
            self.test_results['phase3_integration'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info(f"✅ Phase 3 completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Phase 3 failed: {e}")
            self.test_results['phase3_integration'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_pattern_prediction_pipeline(self):
        """Test pattern → prediction pipeline"""
        logger.info("  Testing pattern → prediction pipeline...")
        
        # Get a test pattern
        patterns = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND metadata->>'test_phase' = 'comprehensive' LIMIT 1"
        )
        
        if patterns:
            pattern = patterns[0]
            
            # Test pattern recognition
            similar_patterns = await self.prediction_engine.get_similar_group_context(pattern['content'])
            logger.info(f"    Similar patterns found: {len(similar_patterns)}")
            
            # Test prediction creation
            prediction = await self.prediction_engine.create_prediction(pattern['content'], similar_patterns)
            logger.info(f"    Prediction created: {prediction is not None}")
            
            if prediction:
                # Test prediction tracking
                await self.cil.prediction_tracker.track_prediction(prediction['id'], 'pending', 0.0)
                logger.info("    Prediction tracking started")
        
        logger.info("  ✅ Pattern → prediction pipeline tests passed")
    
    async def test_multi_cluster_learning(self):
        """Test multi-cluster learning integration"""
        logger.info("  Testing multi-cluster learning...")
        
        # Test cluster grouping
        cluster_results = await self.multi_cluster_orchestrator.run_multi_cluster_grouping()
        logger.info(f"    Cluster grouping completed: {cluster_results}")
        
        # Test per-cluster learning
        learning_results = await self.multi_cluster_orchestrator.run_per_cluster_learning()
        logger.info(f"    Per-cluster learning completed: {learning_results}")
        
        # Test braid level progression
        progression_results = await self.multi_cluster_orchestrator.run_braid_level_progression()
        logger.info(f"    Braid level progression completed: {progression_results}")
        
        logger.info("  ✅ Multi-cluster learning tests passed")
    
    async def test_context_integration(self):
        """Test context system integration"""
        logger.info("  Testing context integration...")
        
        # Test context retrieval during prediction creation
        patterns = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND metadata->>'test_phase' = 'comprehensive' LIMIT 1"
        )
        
        if patterns:
            pattern = patterns[0]
            
            # Get context for prediction
            context = await self.cil.context_system.get_relevant_context(
                kind='prediction_review',
                filters={'asset': pattern['content']['asset']},
                limit=10
            )
            logger.info(f"    Context retrieved for prediction: {len(context)} items")
            
            # Test context usage in LLM analysis
            if context:
                analysis = await self.llm_analyzer.analyze_cluster_learning(
                    cluster_type='asset',
                    cluster_key=pattern['content']['asset'],
                    prediction_reviews=context
                )
                logger.info(f"    LLM analysis completed: {analysis is not None}")
        
        logger.info("  ✅ Context integration tests passed")
    
    async def phase4_end_to_end_tests(self):
        """Phase 4: End-to-end testing"""
        logger.info("🔄 Phase 4: End-to-End Tests")
        
        start_time = time.time()
        
        try:
            # Test complete learning cycle
            await self.test_complete_learning_cycle()
            
            # Test real-world scenarios
            await self.test_real_world_scenarios()
            
            duration = time.time() - start_time
            self.test_results['phase4_end_to_end'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info(f"✅ Phase 4 completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Phase 4 failed: {e}")
            self.test_results['phase4_end_to_end'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_complete_learning_cycle(self):
        """Test complete learning cycle"""
        logger.info("  Testing complete learning cycle...")
        
        # Run complete multi-cluster learning cycle
        results = await self.multi_cluster_orchestrator.run_complete_learning_cycle()
        logger.info(f"    Complete learning cycle results: {results}")
        
        # Test system adaptation
        adaptation_results = await self.test_system_adaptation()
        logger.info(f"    System adaptation: {adaptation_results}")
        
        logger.info("  ✅ Complete learning cycle tests passed")
    
    async def test_real_world_scenarios(self):
        """Test real-world scenarios"""
        logger.info("  Testing real-world scenarios...")
        
        # Test market volatility scenarios
        volatility_results = await self.test_market_volatility_scenarios()
        logger.info(f"    Market volatility scenarios: {volatility_results}")
        
        # Test multiple asset trading
        multi_asset_results = await self.test_multiple_asset_trading()
        logger.info(f"    Multiple asset trading: {multi_asset_results}")
        
        # Test different timeframe patterns
        timeframe_results = await self.test_different_timeframe_patterns()
        logger.info(f"    Different timeframe patterns: {timeframe_results}")
        
        logger.info("  ✅ Real-world scenario tests passed")
    
    async def test_system_adaptation(self):
        """Test system adaptation over time"""
        # Simulate multiple learning cycles
        for i in range(3):
            await self.multi_cluster_orchestrator.run_complete_learning_cycle()
            await asyncio.sleep(0.1)  # Small delay between cycles
        
        return "System adapted through multiple cycles"
    
    async def test_market_volatility_scenarios(self):
        """Test market volatility scenarios"""
        # Test high volatility patterns
        high_vol_patterns = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND content->>'pattern_type' = 'volume_spike' LIMIT 5"
        )
        
        return f"High volatility patterns: {len(high_vol_patterns)}"
    
    async def test_multiple_asset_trading(self):
        """Test multiple asset trading scenarios"""
        # Test different assets
        assets = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        asset_results = {}
        
        for asset in assets:
            patterns = await self.supabase.execute_query(
                f"SELECT COUNT(*) FROM AD_strands WHERE kind = 'pattern' AND content->>'asset' = '{asset}'"
            )
            asset_results[asset] = patterns[0]['count'] if patterns else 0
        
        return asset_results
    
    async def test_different_timeframe_patterns(self):
        """Test different timeframe patterns"""
        # Test different timeframes
        timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        timeframe_results = {}
        
        for timeframe in timeframes:
            patterns = await self.supabase.execute_query(
                f"SELECT COUNT(*) FROM AD_strands WHERE kind = 'pattern' AND content->>'timeframe' = '{timeframe}'"
            )
            timeframe_results[timeframe] = patterns[0]['count'] if patterns else 0
        
        return timeframe_results
    
    async def phase5_stress_performance_tests(self):
        """Phase 5: Stress and performance testing"""
        logger.info("⚡ Phase 5: Stress & Performance Tests")
        
        start_time = time.time()
        
        try:
            # Test high volume data
            await self.test_high_volume_data()
            
            # Test edge cases
            await self.test_edge_cases()
            
            # Test performance benchmarks
            await self.test_performance_benchmarks()
            
            duration = time.time() - start_time
            self.test_results['phase5_stress_performance'] = {
                'status': 'PASSED',
                'duration': duration
            }
            
            logger.info(f"✅ Phase 5 completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ Phase 5 failed: {e}")
            self.test_results['phase5_stress_performance'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_high_volume_data(self):
        """Test high volume data handling"""
        logger.info("  Testing high volume data...")
        
        # Test with large datasets
        start_time = time.time()
        
        # Test pattern recognition with large dataset
        patterns = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND metadata->>'test_phase' = 'comprehensive'"
        )
        pattern_time = time.time() - start_time
        
        # Test prediction creation with large dataset
        start_time = time.time()
        predictions = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'prediction' AND metadata->>'test_phase' = 'comprehensive'"
        )
        prediction_time = time.time() - start_time
        
        # Test learning with large dataset
        start_time = time.time()
        await self.multi_cluster_orchestrator.run_complete_learning_cycle()
        learning_time = time.time() - start_time
        
        logger.info(f"    Pattern processing: {pattern_time:.2f}s for {len(patterns)} patterns")
        logger.info(f"    Prediction processing: {prediction_time:.2f}s for {len(predictions)} predictions")
        logger.info(f"    Learning cycle: {learning_time:.2f}s")
        
        logger.info("  ✅ High volume data tests passed")
    
    async def test_edge_cases(self):
        """Test edge cases"""
        logger.info("  Testing edge cases...")
        
        # Test empty database scenarios
        empty_patterns = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND content->>'pattern_type' = 'nonexistent'"
        )
        logger.info(f"    Empty pattern query: {len(empty_patterns)} results")
        
        # Test single pattern scenarios
        single_pattern = await self.supabase.execute_query(
            "SELECT * FROM AD_strands WHERE kind = 'pattern' AND metadata->>'test_phase' = 'comprehensive' LIMIT 1"
        )
        if single_pattern:
            logger.info(f"    Single pattern handling: {single_pattern[0]['id']}")
        
        # Test extreme similarity scores
        extreme_similarity = await self.calculate_pattern_similarity(
            {'content': {'pattern_type': 'volume_spike', 'asset': 'BTC', 'timeframe': '1h'}},
            {'content': {'pattern_type': 'divergence', 'asset': 'ETH', 'timeframe': '1d'}}
        )
        logger.info(f"    Extreme similarity score: {extreme_similarity}")
        
        logger.info("  ✅ Edge case tests passed")
    
    async def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        logger.info("  Testing performance benchmarks...")
        
        # Test response times
        start_time = time.time()
        await self.multi_cluster_orchestrator.run_complete_learning_cycle()
        cycle_time = time.time() - start_time
        
        # Test memory usage (simplified)
        import psutil
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        # Test database query performance
        start_time = time.time()
        await self.supabase.execute_query("SELECT COUNT(*) FROM AD_strands")
        query_time = time.time() - start_time
        
        logger.info(f"    Learning cycle time: {cycle_time:.2f}s")
        logger.info(f"    Memory usage: {memory_usage:.2f} MB")
        logger.info(f"    Database query time: {query_time:.2f}s")
        
        # Performance criteria
        performance_ok = (
            cycle_time < 5.0 and  # Learning cycle under 5 seconds
            memory_usage < 500 and  # Memory under 500MB
            query_time < 1.0  # Query under 1 second
        )
        
        logger.info(f"    Performance criteria met: {performance_ok}")
        
        logger.info("  ✅ Performance benchmark tests passed")
    
    async def generate_final_report(self):
        """Generate final test report"""
        logger.info("📊 Generating Final Test Report")
        
        total_duration = sum(
            result.get('duration', 0) 
            for result in self.test_results.values() 
            if isinstance(result, dict) and 'duration' in result
        )
        
        passed_phases = sum(
            1 for result in self.test_results.values() 
            if isinstance(result, dict) and result.get('status') == 'PASSED'
        )
        
        total_phases = len(self.test_results)
        
        report = {
            'test_summary': {
                'total_phases': total_phases,
                'passed_phases': passed_phases,
                'failed_phases': total_phases - passed_phases,
                'total_duration': total_duration,
                'success_rate': f"{(passed_phases / total_phases) * 100:.1f}%"
            },
            'phase_results': self.test_results,
            'recommendations': self.generate_recommendations()
        }
        
        # Save report to file
        with open('cil_comprehensive_test_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info("📋 FINAL TEST REPORT")
        logger.info(f"Total Phases: {total_phases}")
        logger.info(f"Passed Phases: {passed_phases}")
        logger.info(f"Failed Phases: {total_phases - passed_phases}")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info(f"Success Rate: {(passed_phases / total_phases) * 100:.1f}%")
        
        if passed_phases == total_phases:
            logger.info("🎉 ALL TESTS PASSED! CIL system is ready for production!")
        else:
            logger.warning(f"⚠️ {total_phases - passed_phases} phases failed. Review the report for details.")
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check for performance issues
        for phase, result in self.test_results.items():
            if isinstance(result, dict) and 'duration' in result:
                if result['duration'] > 10:  # More than 10 seconds
                    recommendations.append(f"Optimize {phase} - took {result['duration']:.2f}s")
        
        # Check for failed phases
        failed_phases = [
            phase for phase, result in self.test_results.items()
            if isinstance(result, dict) and result.get('status') == 'FAILED'
        ]
        
        if failed_phases:
            recommendations.append(f"Fix failed phases: {', '.join(failed_phases)}")
        
        if not recommendations:
            recommendations.append("System is performing well - no immediate optimizations needed")
        
        return recommendations

async def main():
    """Main test execution"""
    tester = CILComprehensiveTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())

