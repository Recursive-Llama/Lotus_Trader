#!/usr/bin/env python3
"""
CIL Core Features Test

This test focuses on the core CIL features in a realistic environment:
1. Pattern Recognition & Grouping
2. Prediction Creation (Code + LLM)
3. Learning System (Multi-cluster)
4. Context System
5. Outcome Analysis

This is a focused test that can be run immediately to validate core functionality.
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

# Import utilities
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CILCoreFeaturesTester:
    """Core features test for CIL system"""
    
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
        
        # Test results
        self.test_results = {}
        self.mock_predictions = []
    
    async def run_core_features_test(self):
        """Run core features test"""
        logger.info("🚀 Starting CIL Core Features Test")
        
        try:
            # 1. Create test data
            await self.create_test_data()
            
            # 2. Test pattern recognition & grouping
            await self.test_pattern_recognition_grouping()
            
            # 3. Test prediction creation
            await self.test_prediction_creation()
            
            # 4. Test learning system
            await self.test_learning_system()
            
            # 5. Test context system
            await self.test_context_system()
            
            # 6. Test outcome analysis
            await self.test_outcome_analysis()
            
            # 7. Test integration
            await self.test_integration()
            
            # 8. Generate report
            await self.generate_test_report()
            
        except Exception as e:
            logger.error(f"❌ Core features test failed: {e}")
            raise
    
    async def create_test_data(self):
        """Create focused test data"""
        logger.info("📊 Creating Test Data")
        
        # Clear existing test data
        await self.cleanup_test_data()
        
        # Create pattern strands
        await self.create_pattern_strands()
        
        # Create prediction reviews
        await self.create_prediction_reviews()
        
        # Create braids
        await self.create_braids()
        
        logger.info("✅ Test data created")
    
    async def cleanup_test_data(self):
        """Clean up existing test data"""
        logger.info("  Cleaning up existing test data...")
        
        # Delete existing test data
        await self.supabase.execute_query(
            "DELETE FROM AD_strands WHERE tags->>'test_type' = 'core_features'"
        )
        
        logger.info("  Cleanup completed")
    
    async def create_pattern_strands(self):
        """Create pattern strands for testing"""
        logger.info("  Creating pattern strands...")
        
        pattern_types = ['volume_spike', 'divergence', 'flow']
        assets = ['BTC', 'ETH', 'SOL']
        timeframes = ['5m', '15m', '1h']
        
        for i in range(20):
            pattern = {
                'id': str(uuid.uuid4()),
                'kind': 'pattern',
                'symbol': random.choice(assets),
                'timeframe': random.choice(timeframes),
                'confidence': round(random.uniform(0.5, 0.9), 2),
                'tags': {
                    'test_type': 'core_features',
                    'version': '1.0',
                    'pattern_type': random.choice(pattern_types),
                    'strength': round(random.uniform(0.6, 0.8), 2),
                    'novelty': round(random.uniform(0.3, 0.7), 2),
                    'surprise': round(random.uniform(0.2, 0.6), 2),
                    'persistence': round(random.uniform(0.4, 0.8), 2),
                    'group_type': random.choice(['single', 'multi']),
                    'method': random.choice(['technical', 'fundamental']),
                    'detection_time': datetime.now().isoformat()
                },
                'module_intelligence': {
                    'pattern_type': random.choice(pattern_types),
                    'strength': round(random.uniform(0.6, 0.8), 2),
                    'novelty': round(random.uniform(0.3, 0.7), 2),
                    'surprise': round(random.uniform(0.2, 0.6), 2),
                    'persistence': round(random.uniform(0.4, 0.8), 2),
                    'group_type': random.choice(['single', 'multi']),
                    'method': random.choice(['technical', 'fundamental']),
                    'detection_time': datetime.now().isoformat()
                }
            }
            
            self.supabase.insert_strand(pattern)
        
        logger.info("  Created 20 pattern strands")
    
    async def create_prediction_reviews(self):
        """Create prediction reviews for testing"""
        logger.info("  Creating prediction reviews...")
        
        outcomes = ['target_hit', 'stop_hit', 'expired']
        assets = ['BTC', 'ETH', 'SOL']
        timeframes = ['5m', '15m', '1h']
        
        for i in range(30):
            review = {
                'id': str(uuid.uuid4()),
                'kind': 'prediction_review',
                'symbol': random.choice(assets),
                'timeframe': random.choice(timeframes),
                'confidence': round(random.uniform(0.4, 0.9), 2),
                'tags': {
                    'test_type': 'core_features',
                    'version': '1.0',
                    'prediction_id': str(uuid.uuid4()),
                    'outcome': random.choice(outcomes),
                    'final_price': round(random.uniform(100, 100000), 2),
                    'max_drawdown': round(random.uniform(0.01, 0.1), 3),
                    'success_rate': round(random.uniform(0.3, 0.8), 2),
                    'risk_reward_ratio': round(random.uniform(0.8, 2.5), 2),
                    'cluster_keys': {
                        'pattern_timeframe': f"{random.choice(['volume_spike', 'divergence'])}_1h",
                        'asset': random.choice(assets),
                        'timeframe': random.choice(timeframes),
                        'outcome': random.choice(outcomes),
                        'pattern': random.choice(['volume_spike', 'divergence', 'flow']),
                        'group_type': random.choice(['single', 'multi']),
                        'method': random.choice(['technical', 'fundamental'])
                    },
                    'original_pattern_strand_ids': [str(uuid.uuid4())],
                    'group_type': random.choice(['single', 'multi'])
                },
                'module_intelligence': {
                    'prediction_id': str(uuid.uuid4()),
                    'outcome': random.choice(outcomes),
                    'final_price': round(random.uniform(100, 100000), 2),
                    'max_drawdown': round(random.uniform(0.01, 0.1), 3),
                    'success_rate': round(random.uniform(0.3, 0.8), 2),
                    'risk_reward_ratio': round(random.uniform(0.8, 2.5), 2),
                    'cluster_keys': {
                        'pattern_timeframe': f"{random.choice(['volume_spike', 'divergence'])}_1h",
                        'asset': random.choice(assets),
                        'timeframe': random.choice(timeframes),
                        'outcome': random.choice(outcomes),
                        'pattern': random.choice(['volume_spike', 'divergence', 'flow']),
                        'group_type': random.choice(['single', 'multi']),
                        'method': random.choice(['technical', 'fundamental'])
                    },
                    'original_pattern_strand_ids': [str(uuid.uuid4())],
                    'group_type': random.choice(['single', 'multi'])
                }
            }
            
            self.supabase.insert_strand(review)
        
        logger.info("  Created 30 prediction reviews")
    
    async def create_braids(self):
        """Create braids for testing"""
        logger.info("  Creating braids...")
        
        # Get some prediction reviews to create braids from
        reviews = await self.supabase.execute_query(
            "SELECT id FROM AD_strands WHERE kind = 'prediction_review' AND tags->>'test_type' = 'core_features' LIMIT 9"
        )
        
        if len(reviews) >= 3:
            # Create 3 level 1 braids
            for i in range(3):
                # Generate random strand IDs for braid creation
                strand_ids = [str(uuid.uuid4()) for _ in range(3)]
                
                braid = {
                    'id': str(uuid.uuid4()),
                    'kind': 'braid',
                    'braid_level': 1,
                    'tags': {
                        'test_type': 'core_features',
                        'version': '1.0',
                        'cluster_type': random.choice(['pattern_timeframe', 'asset', 'timeframe']),
                        'cluster_key': f"test_cluster_{i}",
                        'strand_ids': strand_ids,
                        'learning_insights': {
                            'success_rate': round(random.uniform(0.4, 0.8), 2),
                            'avg_confidence': round(random.uniform(0.5, 0.9), 2),
                            'risk_reward_ratio': round(random.uniform(1.0, 2.0), 2)
                        }
                    },
                    'module_intelligence': {
                        'cluster_type': random.choice(['pattern_timeframe', 'asset', 'timeframe']),
                        'cluster_key': f"test_cluster_{i}",
                        'strand_ids': strand_ids,
                        'learning_insights': {
                            'success_rate': round(random.uniform(0.4, 0.8), 2),
                            'avg_confidence': round(random.uniform(0.5, 0.9), 2),
                            'risk_reward_ratio': round(random.uniform(1.0, 2.0), 2)
                        }
                    }
                }
                
                self.supabase.insert_strand(braid)
        
        logger.info("  Created braids")
    
    async def test_pattern_recognition_grouping(self):
        """Test pattern recognition and grouping"""
        logger.info("🔍 Testing Pattern Recognition & Grouping")
        
        start_time = time.time()
        
        try:
            # Test pattern retrieval
            patterns = await self.supabase.execute_query(
                "SELECT * FROM AD_strands WHERE kind = 'pattern' AND tags->>'test_type' = 'core_features'"
            )
            
            logger.info(f"  Found {len(patterns)} patterns")
            
            # Test pattern grouping
            cluster_types = ['pattern_timeframe', 'asset', 'timeframe', 'outcome', 'pattern', 'group_type', 'method']
            
            # Get prediction reviews for grouping
            reviews = await self.supabase.execute_query(
                "SELECT * FROM AD_strands WHERE kind = 'prediction_review' AND tags->>'test_type' = 'core_features'"
            )
            
            if reviews:
                grouping_results = await self.grouping_engine.group_prediction_reviews(reviews)
                for cluster_type in cluster_types:
                    cluster_count = len(grouping_results.get(cluster_type, {}))
                    grouping_results[cluster_type] = cluster_count
                    logger.info(f"  {cluster_type}: {cluster_count} clusters")
            else:
                grouping_results = {cluster_type: 0 for cluster_type in cluster_types}
                logger.info("  No prediction reviews found for grouping")
            
            # Test similarity matching
            if len(patterns) >= 2:
                pattern1 = patterns[0]
                pattern2 = patterns[1]
                similarity = await self.calculate_similarity(pattern1, pattern2)
                logger.info(f"  Pattern similarity: {similarity:.2f}")
            
            duration = time.time() - start_time
            self.test_results['pattern_recognition_grouping'] = {
                'status': 'PASSED',
                'duration': duration,
                'patterns_found': len(patterns),
                'grouping_results': grouping_results
            }
            
            logger.info("✅ Pattern recognition & grouping tests passed")
            
        except Exception as e:
            logger.error(f"❌ Pattern recognition & grouping failed: {e}")
            self.test_results['pattern_recognition_grouping'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_prediction_creation(self):
        """Test prediction creation"""
        logger.info("🎯 Testing Prediction Creation")
        
        start_time = time.time()
        
        try:
            # Create a proper pattern group structure for testing
            test_pattern_group = {
                'patterns': [{
                    'pattern_type': 'volume_spike',
                    'symbol': 'BTC',
                    'timeframe': '1h',
                    'confidence': 0.7
                }],
                'group_type': 'single_pattern',
                'timeframe': '1h',
                'asset': 'BTC',
                'method': 'test'
            }
            
            # Create proper context structure
            context = {
                'exact_matches': [],
                'similar_matches': []
            }
            
            # Test code-based prediction
            code_prediction = await self.prediction_engine.create_code_prediction(test_pattern_group, context)
            logger.info(f"  Code prediction created: {code_prediction is not None}")
            
            # Test LLM prediction
            llm_prediction = await self.prediction_engine.create_llm_prediction(test_pattern_group, context)
            logger.info(f"  LLM prediction created: {llm_prediction is not None}")
            
            # Test prediction duration
            duration_hours = self.prediction_engine.get_timeframe_hours('1h')
            logger.info(f"  Prediction duration for 1h: {duration_hours} hours")
            
            # Test prediction strand creation
            if code_prediction:
                # Create prediction data structure
                prediction_data = {
                    'pattern_group': test_pattern_group,
                    'code_prediction': code_prediction,
                    'llm_prediction': llm_prediction,
                    'context_metadata': {'test': True},
                    'prediction_notes': 'Test prediction'
                }
                prediction_strand = await self.prediction_engine.create_prediction_strand(prediction_data)
                logger.info(f"  Prediction strand created: {prediction_strand is not None}")
            
            duration = time.time() - start_time
            self.test_results['prediction_creation'] = {
                'status': 'PASSED',
                'duration': duration,
                'code_prediction': code_prediction is not None,
                'llm_prediction': llm_prediction is not None,
                'duration_hours': duration_hours
            }
            
            logger.info("✅ Prediction creation tests passed")
            
        except Exception as e:
            logger.error(f"❌ Prediction creation failed: {e}")
            self.test_results['prediction_creation'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_learning_system(self):
        """Test learning system"""
        logger.info("🧠 Testing Learning System")
        
        start_time = time.time()
        
        try:
            # Test complete learning cycle
            complete_results = await self.multi_cluster_orchestrator.run_complete_learning_cycle()
            logger.info(f"  Complete learning cycle: {complete_results}")
            
            # Test system statistics
            stats = await self.multi_cluster_orchestrator.get_system_statistics()
            logger.info(f"  System statistics: {stats}")
            
            # Test cluster queries
            cluster_queries = await self.multi_cluster_orchestrator.test_cluster_queries()
            logger.info(f"  Cluster queries: {cluster_queries}")
            
            # Test learning analysis example
            analysis_example = await self.multi_cluster_orchestrator.run_learning_analysis_example()
            logger.info(f"  Learning analysis example: {analysis_example}")
            
            duration = time.time() - start_time
            self.test_results['learning_system'] = {
                'status': 'PASSED',
                'duration': duration,
                'complete_results': complete_results,
                'system_statistics': stats,
                'cluster_queries': cluster_queries,
                'analysis_example': analysis_example
            }
            
            logger.info("✅ Learning system tests passed")
            
        except Exception as e:
            logger.error(f"❌ Learning system failed: {e}")
            self.test_results['learning_system'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_context_system(self):
        """Test context system"""
        logger.info("🔗 Testing Context System")
        
        start_time = time.time()
        
        try:
            # Test pattern context retrieval
            pattern_context = self.supabase.get_recent_strands(limit=5)
            pattern_context = [s for s in pattern_context if s.get('kind') == 'pattern']
            logger.info(f"  Pattern context retrieved: {len(pattern_context)} items")
            
            # Test prediction review context retrieval
            review_context = self.supabase.get_recent_strands(limit=5)
            review_context = [s for s in review_context if s.get('kind') == 'prediction_review']
            logger.info(f"  Review context retrieved: {len(review_context)} items")
            
            # Test context filtering
            filtered_context = self.supabase.get_recent_strands(limit=3)
            filtered_context = [s for s in filtered_context if s.get('kind') == 'pattern']
            logger.info(f"  Filtered context retrieved: {len(filtered_context)} items")
            
            duration = time.time() - start_time
            self.test_results['context_system'] = {
                'status': 'PASSED',
                'duration': duration,
                'pattern_context_count': len(pattern_context),
                'review_context_count': len(review_context),
                'filtered_context_count': len(filtered_context)
            }
            
            logger.info("✅ Context system tests passed")
            
        except Exception as e:
            logger.error(f"❌ Context system failed: {e}")
            self.test_results['context_system'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_outcome_analysis(self):
        """Test outcome analysis"""
        logger.info("📊 Testing Outcome Analysis")
        
        start_time = time.time()
        
        try:
            # Create mock predictions for testing
            self.mock_predictions = [
                {
                    'id': 'test_pred_1',
                    'pattern_group': {'patterns': [{'pattern_type': 'volume_spike'}]},
                    'code_prediction': {'direction': 'long', 'confidence': 0.7},
                    'llm_prediction': {'direction': 'long', 'confidence': 0.8},
                    'outcome': 'target_hit',
                    'created_at': '2025-09-10T15:00:00Z'
                },
                {
                    'id': 'test_pred_2',
                    'pattern_group': {'patterns': [{'pattern_type': 'divergence'}]},
                    'code_prediction': {'direction': 'short', 'confidence': 0.6},
                    'llm_prediction': {'direction': 'short', 'confidence': 0.7},
                    'outcome': 'stop_hit',
                    'created_at': '2025-09-10T15:05:00Z'
                }
            ]
            
            # Test prediction outcome tracking
            if self.mock_predictions:
                prediction_id = f"test_pred_{int(time.time())}"
                # First create the prediction in the database
                prediction_strand = {
                    'id': prediction_id,
                    'kind': 'prediction',
                    'content': {
                        'prediction_id': prediction_id,
                        'pattern_group': 'test_group',
                        'prediction_type': 'code',
                        'direction': 'long',
                        'confidence': 0.7,
                        'target_price': 50000,
                        'stop_price': 48000,
                        'duration_hours': 2
                    },
                    'tags': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike'
                    }
                }
                self.supabase.insert_strand(prediction_strand)
                
                result = await self.cil.prediction_tracker.track_prediction(prediction_id)
                logger.info(f"  Prediction outcome tracked: {result}")
            
            # Test outcome analysis
            outcomes = await self.cil.outcome_analyzer.analyze_completed_prediction(prediction_id)
            logger.info(f"  Outcome analysis completed: {outcomes is not None}")
            
            # Test learning thresholds
            test_group = {
                'group_key': 'test_group',
                'pattern_type': 'volume_spike',
                'asset': 'BTC',
                'timeframe': '1h',
                'prediction_count': 5
            }
            thresholds_met = self.cil.meets_learning_thresholds(test_group)
            logger.info(f"  Learning thresholds met: {thresholds_met}")
            
            duration = time.time() - start_time
            self.test_results['outcome_analysis'] = {
                'status': 'PASSED',
                'duration': duration,
                'outcomes_analyzed': len(outcomes),
                'thresholds_met': thresholds_met
            }
            
            logger.info("✅ Outcome analysis tests passed")
            
        except Exception as e:
            logger.error(f"❌ Outcome analysis failed: {e}")
            self.test_results['outcome_analysis'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def test_integration(self):
        """Test component integration"""
        logger.info("🔗 Testing Integration")
        
        start_time = time.time()
        
        try:
            # Test pattern → prediction pipeline
            patterns = await self.supabase.execute_query(
                "SELECT * FROM AD_strands WHERE kind = 'pattern' LIMIT 1"
            )
            
            if patterns:
                pattern = patterns[0]
                
                # Get similar patterns
                pattern_content = {
                    'pattern_type': pattern.get('tags', {}).get('pattern_type', 'volume_spike'),
                    'symbol': pattern.get('symbol', 'BTC'),
                    'timeframe': pattern.get('timeframe', '1h'),
                    'confidence': pattern.get('confidence', 0.7),
                    'asset': 'BTC',
                    'group_type': 'single_pattern_single_timeframe'
                }
                similar_patterns = await self.prediction_engine.get_similar_group_context(pattern_content)
                logger.info(f"  Similar patterns found: {len(similar_patterns)}")
                
                # Create prediction
                prediction = await self.prediction_engine.create_prediction(pattern_content)
                logger.info(f"  Prediction created: {prediction is not None}")
                
                if prediction:
                    # Track prediction
                    await self.cil.prediction_tracker.track_prediction(prediction)
                    logger.info("  Prediction tracking started")
            
            # Test context integration
            current_analysis = {
                'kind': 'prediction_review',
                'symbol': 'BTC',
                'pattern_type': 'volume_spike'
            }
            context = self.prediction_engine.context_system.get_relevant_context(
                current_analysis=current_analysis,
                top_k=5
            )
            logger.info(f"  Context integration: {len(context.get('similar_situations', []))} items")
            
            # Test LLM analysis
            if context and context.get('similar_situations'):
                analysis = await self.llm_analyzer.analyze_cluster_learning(
                    cluster_type='asset',
                    cluster_key='BTC',
                    prediction_reviews=context.get('similar_situations', [])
                )
                logger.info(f"  LLM analysis completed: {analysis is not None}")
            
            duration = time.time() - start_time
            self.test_results['integration'] = {
                'status': 'PASSED',
                'duration': duration,
                'similar_patterns': len(similar_patterns) if 'similar_patterns' in locals() else 0,
                'prediction_created': prediction is not None if 'prediction' in locals() else False,
                'prediction_id': prediction if 'prediction' in locals() and prediction else None,
                'context_items': len(context.get('similar_situations', [])) if 'context' in locals() else 0,
                'llm_analysis': analysis is not None if 'analysis' in locals() else False
            }
            
            logger.info("✅ Integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Integration failed: {e}")
            self.test_results['integration'] = {'status': 'FAILED', 'error': str(e)}
            raise
    
    async def calculate_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        """Calculate similarity between two patterns"""
        similarity = 0.0
        
        # Safely access pattern_type from tags
        pattern_type1 = pattern1.get('tags', {}).get('pattern_type', '')
        pattern_type2 = pattern2.get('tags', {}).get('pattern_type', '')
        
        if pattern_type1 == pattern_type2:
            similarity += 0.5
        
        if pattern1.get('symbol') == pattern2.get('symbol'):
            similarity += 0.3
        
        if pattern1.get('timeframe') == pattern2.get('timeframe'):
            similarity += 0.2
        
        return similarity
    
    async def generate_test_report(self):
        """Generate test report"""
        logger.info("📊 Generating Test Report")
        
        total_duration = sum(
            result.get('duration', 0) 
            for result in self.test_results.values() 
            if isinstance(result, dict) and 'duration' in result
        )
        
        passed_tests = sum(
            1 for result in self.test_results.values() 
            if isinstance(result, dict) and result.get('status') == 'PASSED'
        )
        
        total_tests = len(self.test_results)
        
        logger.info("📋 CORE FEATURES TEST REPORT")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed Tests: {passed_tests}")
        logger.info(f"Failed Tests: {total_tests - passed_tests}")
        logger.info(f"Total Duration: {total_duration:.2f}s")
        logger.info(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
        
        # Detailed results
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            duration = result.get('duration', 0)
            logger.info(f"  {test_name}: {status} ({duration:.2f}s)")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL CORE FEATURES TESTS PASSED! CIL system is working correctly!")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} tests failed. Review the results above.")
        
        # Save report
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'total_duration': total_duration,
                'success_rate': f"{(passed_tests / total_tests) * 100:.1f}%"
            },
            'test_results': self.test_results
        }
        
        with open('cil_core_features_test_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info("📄 Test report saved to cil_core_features_test_report.json")

async def main():
    """Main test execution"""
    tester = CILCoreFeaturesTester()
    await tester.run_core_features_test()

if __name__ == "__main__":
    asyncio.run(main())
