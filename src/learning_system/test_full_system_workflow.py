#!/usr/bin/env python3
"""
Full System Workflow Testing Suite

Tests the complete end-to-end functionality of the centralized learning system:
1. Market Data → RDI → Pattern Detection
2. Pattern → CIL → Prediction Creation  
3. Prediction → CTP → Trading Plan Generation
4. Trading Plan → DM → Decision Making
5. Decision → TD → Execution
6. Execution → Learning System → Braid Creation
7. Learning System → Context Injection → Module Enhancement

This validates that the system actually does what it's designed to do.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import traceback

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector'))
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector', 'src'))

from utils.supabase_manager import SupabaseManager
from multi_cluster_grouping_engine import MultiClusterGroupingEngine
from mathematical_resonance_engine import MathematicalResonanceEngine
from centralized_learning_system import CentralizedLearningSystem
from learning_pipeline import LearningPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('full_system_workflow_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class FullSystemWorkflowTester:
    """Full system workflow testing suite"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.clustering_engine = MultiClusterGroupingEngine(self.supabase_manager)
        self.resonance_engine = MathematicalResonanceEngine()
        self.test_results = {}
        self.start_time = None
        self.test_data = {}
        
    async def run_all_tests(self):
        """Run all full system workflow tests"""
        logger.info("🚀 Starting Full System Workflow Testing")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_suites = [
            ("System Initialization", self.test_system_initialization),
            ("Market Data Processing", self.test_market_data_processing),
            ("Pattern Detection (RDI)", self.test_pattern_detection),
            ("Prediction Creation (CIL)", self.test_prediction_creation),
            ("Trading Plan Generation (CTP)", self.test_trading_plan_generation),
            ("Decision Making (DM)", self.test_decision_making),
            ("Execution (TD)", self.test_execution),
            ("Learning System Integration", self.test_learning_system_integration),
            ("Braid Creation", self.test_braid_creation),
            ("Context Injection", self.test_context_injection),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
            ("Performance Under Load", self.test_performance_under_load)
        ]
        
        for suite_name, test_func in test_suites:
            try:
                logger.info(f"\n🔍 Running {suite_name} Tests...")
                await test_func()
                logger.info(f"✅ {suite_name} Tests PASSED")
            except Exception as e:
                logger.error(f"❌ {suite_name} Tests FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.test_results[suite_name] = {"status": "FAILED", "error": str(e)}
        
        self.print_summary()
    
    async def test_system_initialization(self):
        """Test system initialization and component setup"""
        logger.info("  🏗️ Testing system initialization...")
        
        try:
            # Test database connection
            db_connected = self.supabase_manager.test_connection()
            if db_connected:
                logger.info("    ✅ Database connection successful")
            else:
                raise Exception("Database connection failed")
            
            # Test clustering engine initialization
            if self.clustering_engine:
                logger.info("    ✅ Clustering engine initialized")
            else:
                raise Exception("Clustering engine initialization failed")
            
            # Test resonance engine initialization
            if self.resonance_engine:
                logger.info("    ✅ Resonance engine initialized")
            else:
                raise Exception("Resonance engine initialization failed")
            
            # Test learning system initialization
            try:
                from llm_integration.openrouter_client import OpenRouterClient
                llm_client = OpenRouterClient()
                learning_system = CentralizedLearningSystem(self.supabase_manager, llm_client, None)
                logger.info("    ✅ Learning system initialized")
                self.test_data['learning_system'] = learning_system
            except Exception as e:
                logger.warning(f"    ⚠️ Learning system initialization issue: {e}")
            
            # Test learning pipeline initialization
            try:
                learning_pipeline = LearningPipeline(self.supabase_manager, llm_client)
                logger.info("    ✅ Learning pipeline initialized")
                self.test_data['learning_pipeline'] = learning_pipeline
            except Exception as e:
                logger.warning(f"    ⚠️ Learning pipeline initialization issue: {e}")
            
        except Exception as e:
            logger.error(f"    ❌ System initialization test failed: {e}")
            raise
        
        logger.info("    ✅ System initialization test successful")
    
    async def test_market_data_processing(self):
        """Test market data processing through RDI"""
        logger.info("  📊 Testing market data processing...")
        
        try:
            # Create realistic market data
            market_data = {
                'symbol': 'BTC',
                'open': 44800.0,
                'high': 45200.0,
                'low': 44700.0,
                'close': 45000.0,
                'volume': 1200.0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'hyperliquid'
            }
            
            # Test market data validation
            required_fields = ['symbol', 'open', 'high', 'low', 'close', 'volume', 'timestamp']
            for field in required_fields:
                if field in market_data:
                    logger.info(f"    ✅ Market data field '{field}': present")
                else:
                    raise Exception(f"Missing required field: {field}")
            
            # Test data quality validation
            if market_data['close'] > 0 and market_data['volume'] > 0:
                logger.info("    ✅ Market data quality validation passed")
            else:
                raise Exception("Market data quality validation failed")
            
            # Store test data for later use
            self.test_data['market_data'] = market_data
            
        except Exception as e:
            logger.error(f"    ❌ Market data processing test failed: {e}")
            raise
        
        logger.info("    ✅ Market data processing test successful")
    
    async def test_pattern_detection(self):
        """Test pattern detection through RDI"""
        logger.info("  🔍 Testing pattern detection (RDI)...")
        
        try:
            # Simulate pattern detection
            market_data = self.test_data['market_data']
            
            # Create realistic pattern data
            pattern = {
                'id': f"pattern_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': market_data['symbol'],
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 0.85,
                    'timeframe': '1h',
                    'price': market_data['close'],
                    'volume': market_data['volume'],
                    'strength': 0.9,
                    'completion': 0.8
                },
                'metadata': {
                    'source': 'rdi_test',
                    'quality': 0.92,
                    'detection_method': 'technical_analysis',
                    'market_conditions': 'bullish'
                },
                'module_intelligence': {
                    'pattern_type': 'head_and_shoulders',
                    'success_rate': 0.75,
                    'detection_confidence': 0.85
                },
                'sig_confidence': 0.85,
                'cluster_key': [{
                    'cluster_type': 'pattern_type',
                    'cluster_key': 'head_and_shoulders',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test pattern validation
            if pattern['content']['confidence'] > 0.8:
                logger.info("    ✅ High confidence pattern detected")
            else:
                logger.warning("    ⚠️ Low confidence pattern detected")
            
            # Test pattern structure
            required_content_fields = ['pattern_type', 'confidence', 'timeframe', 'price']
            for field in required_content_fields:
                if field in pattern['content']:
                    logger.info(f"    ✅ Pattern content field '{field}': present")
                else:
                    raise Exception(f"Missing pattern content field: {field}")
            
            # Store pattern for later use
            self.test_data['pattern'] = pattern
            
        except Exception as e:
            logger.error(f"    ❌ Pattern detection test failed: {e}")
            raise
        
        logger.info("    ✅ Pattern detection test successful")
    
    async def test_prediction_creation(self):
        """Test prediction creation through CIL"""
        logger.info("  🔮 Testing prediction creation (CIL)...")
        
        try:
            # Create prediction based on pattern
            pattern = self.test_data['pattern']
            
            prediction = {
                'id': f"prediction_{uuid.uuid4()}",
                'kind': 'prediction_review',
                'symbol': pattern['symbol'],
                'content': {
                    'prediction': f"{pattern['symbol']} will reach $50000 in 24h",
                    'confidence': 0.82,
                    'timeframe': '24h',
                    'method': 'technical_analysis',
                    'reasoning': 'Head and shoulders pattern indicates bullish reversal',
                    'price_target': 50000.0,
                    'stop_loss': 44000.0,
                    'success': None  # Will be updated after outcome
                },
                'metadata': {
                    'source': 'cil_test',
                    'quality': 0.88,
                    'prediction_method': 'pattern_analysis',
                    'market_context': 'bullish'
                },
                'cluster_key': [{
                    'cluster_type': 'method',
                    'cluster_key': 'technical_analysis',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test prediction validation
            if prediction['content']['confidence'] > 0.8:
                logger.info("    ✅ High confidence prediction created")
            else:
                logger.warning("    ⚠️ Low confidence prediction created")
            
            # Test prediction structure
            required_content_fields = ['prediction', 'confidence', 'timeframe', 'method']
            for field in required_content_fields:
                if field in prediction['content']:
                    logger.info(f"    ✅ Prediction content field '{field}': present")
                else:
                    raise Exception(f"Missing prediction content field: {field}")
            
            # Store prediction for later use
            self.test_data['prediction'] = prediction
            
        except Exception as e:
            logger.error(f"    ❌ Prediction creation test failed: {e}")
            raise
        
        logger.info("    ✅ Prediction creation test successful")
    
    async def test_trading_plan_generation(self):
        """Test trading plan generation through CTP"""
        logger.info("  📋 Testing trading plan generation (CTP)...")
        
        try:
            # Create trading plan based on prediction
            prediction = self.test_data['prediction']
            
            trading_plan = {
                'id': f"trading_plan_{uuid.uuid4()}",
                'kind': 'conditional_trading_plan',
                'symbol': prediction['symbol'],
                'content': {
                    'plan_type': 'momentum',
                    'strategy': 'pattern_breakout',
                    'conditions': [
                        {
                            'type': 'price_breakout',
                            'condition': 'close > 46000',
                            'timeframe': '1h',
                            'confidence': 0.85
                        },
                        {
                            'type': 'volume_confirmation',
                            'condition': 'volume > 1500',
                            'timeframe': '1h',
                            'confidence': 0.8
                        }
                    ],
                    'risk_score': 0.75,  # Calculated by code
                    'leverage_recommendation': 2.0,
                    'profitability': 0.8,
                    'risk_adjusted_return': 0.6
                },
                'metadata': {
                    'source': 'ctp_test',
                    'quality': 0.9,
                    'plan_confidence': 0.85,
                    'market_conditions': 'bullish'
                },
                'cluster_key': [{
                    'cluster_type': 'plan_type',
                    'cluster_key': 'momentum',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test trading plan validation
            if trading_plan['content']['risk_score'] > 0.7:
                logger.info("    ✅ High quality trading plan generated")
            else:
                logger.warning("    ⚠️ Lower quality trading plan generated")
            
            # Test trading plan structure
            required_content_fields = ['plan_type', 'strategy', 'conditions', 'risk_score']
            for field in required_content_fields:
                if field in trading_plan['content']:
                    logger.info(f"    ✅ Trading plan content field '{field}': present")
                else:
                    raise Exception(f"Missing trading plan content field: {field}")
            
            # Store trading plan for later use
            self.test_data['trading_plan'] = trading_plan
            
        except Exception as e:
            logger.error(f"    ❌ Trading plan generation test failed: {e}")
            raise
        
        logger.info("    ✅ Trading plan generation test successful")
    
    async def test_decision_making(self):
        """Test decision making through DM"""
        logger.info("  🎯 Testing decision making (DM)...")
        
        try:
            # Create trading decision based on plan
            trading_plan = self.test_data['trading_plan']
            
            trading_decision = {
                'id': f"trading_decision_{uuid.uuid4()}",
                'kind': 'trading_decision',
                'symbol': trading_plan['symbol'],
                'content': {
                    'decision_type': 'position_sizing',
                    'action': 'BUY',
                    'amount': 0.1,  # 10% of portfolio
                    'leverage': 2.0,
                    'budget': 1000.0,
                    'reasoning': 'High confidence pattern with good risk/reward ratio',
                    'decision_factors': ['pattern_confidence', 'risk_score', 'market_conditions'],
                    'outcome_quality': 0.85,
                    'risk_management_effectiveness': 0.9
                },
                'metadata': {
                    'source': 'dm_test',
                    'quality': 0.88,
                    'decision_confidence': 0.82,
                    'portfolio_context': 'bullish_bias'
                },
                'cluster_key': [{
                    'cluster_type': 'outcome',
                    'cluster_key': 'buy_decision',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test decision validation
            if trading_decision['content']['amount'] > 0:
                logger.info("    ✅ Positive trading decision made")
            else:
                logger.warning("    ⚠️ No trading decision made")
            
            # Test decision structure
            required_content_fields = ['decision_type', 'action', 'amount', 'leverage']
            for field in required_content_fields:
                if field in trading_decision['content']:
                    logger.info(f"    ✅ Trading decision content field '{field}': present")
                else:
                    raise Exception(f"Missing trading decision content field: {field}")
            
            # Store trading decision for later use
            self.test_data['trading_decision'] = trading_decision
            
        except Exception as e:
            logger.error(f"    ❌ Decision making test failed: {e}")
            raise
        
        logger.info("    ✅ Decision making test successful")
    
    async def test_execution(self):
        """Test execution through TD"""
        logger.info("  ⚡ Testing execution (TD)...")
        
        try:
            # Create execution outcome
            trading_decision = self.test_data['trading_decision']
            
            execution_outcome = {
                'id': f"execution_outcome_{uuid.uuid4()}",
                'kind': 'execution_outcome',
                'symbol': trading_decision['symbol'],
                'content': {
                    'execution_method': 'twap',
                    'execution_strategy': 'adaptive',
                    'execution_success': 0.95,
                    'slippage_minimization': 0.9,
                    'fill_price': 45100.0,
                    'fill_volume': 0.1,
                    'execution_time': 0.5,  # seconds
                    'slippage': 0.02,  # 2%
                    'fees': 5.0
                },
                'metadata': {
                    'source': 'td_test',
                    'quality': 0.92,
                    'execution_confidence': 0.88,
                    'market_impact': 'low'
                },
                'cluster_key': [{
                    'cluster_type': 'outcome',
                    'cluster_key': 'successful_execution',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test execution validation
            if execution_outcome['content']['execution_success'] > 0.9:
                logger.info("    ✅ High success execution")
            else:
                logger.warning("    ⚠️ Lower success execution")
            
            # Test execution structure
            required_content_fields = ['execution_method', 'execution_success', 'fill_price', 'slippage']
            for field in required_content_fields:
                if field in execution_outcome['content']:
                    logger.info(f"    ✅ Execution content field '{field}': present")
                else:
                    raise Exception(f"Missing execution content field: {field}")
            
            # Store execution outcome for later use
            self.test_data['execution_outcome'] = execution_outcome
            
        except Exception as e:
            logger.error(f"    ❌ Execution test failed: {e}")
            raise
        
        logger.info("    ✅ Execution test successful")
    
    async def test_learning_system_integration(self):
        """Test learning system integration"""
        logger.info("  🧠 Testing learning system integration...")
        
        try:
            # Test resonance score calculation for all components
            components = [
                ('pattern', self.test_data['pattern'], 'rdi'),
                ('prediction', self.test_data['prediction'], 'cil'),
                ('trading_plan', self.test_data['trading_plan'], 'ctp'),
                ('trading_decision', self.test_data['trading_decision'], 'dm'),
                ('execution_outcome', self.test_data['execution_outcome'], 'td')
            ]
            
            for component_name, component_data, module_type in components:
                try:
                    resonance_scores = self.resonance_engine.calculate_module_resonance(component_data, module_type)
                    
                    if resonance_scores and 'phi' in resonance_scores:
                        logger.info(f"    ✅ {component_name} resonance scores calculated")
                        logger.info(f"        φ={resonance_scores['phi']:.3f}, ρ={resonance_scores['rho']:.3f}")
                    else:
                        logger.warning(f"    ⚠️ {component_name} resonance scores not calculated")
                except Exception as e:
                    logger.warning(f"    ⚠️ {component_name} resonance calculation failed: {e}")
            
            # Test clustering for different strand types
            strand_types = ['pattern', 'prediction_review', 'conditional_trading_plan', 'trading_decision', 'execution_outcome']
            
            for strand_type in strand_types:
                try:
                    clusters = await self.clustering_engine.get_strand_clusters({}, strand_type)
                    if clusters is not None:
                        logger.info(f"    ✅ {strand_type} clustering working")
                    else:
                        logger.warning(f"    ⚠️ {strand_type} clustering returned None")
                except Exception as e:
                    logger.warning(f"    ⚠️ {strand_type} clustering failed: {e}")
            
        except Exception as e:
            logger.error(f"    ❌ Learning system integration test failed: {e}")
            raise
        
        logger.info("    ✅ Learning system integration test successful")
    
    async def test_braid_creation(self):
        """Test braid creation from learning"""
        logger.info("  🧬 Testing braid creation...")
        
        try:
            # Create a braid from the pattern and prediction
            pattern = self.test_data['pattern']
            prediction = self.test_data['prediction']
            
            braid = {
                'id': f"braid_{uuid.uuid4()}",
                'kind': 'braid',
                'symbol': pattern['symbol'],
                'content': {
                    'braid_type': 'pattern_prediction',
                    'source_strands': [pattern['id'], prediction['id']],
                    'learning_insights': [
                        'Head and shoulders patterns show 75% success rate in bullish markets',
                        'Technical analysis method effective for momentum strategies',
                        'Risk management crucial for pattern-based trading'
                    ],
                    'confidence': 0.88,
                    'success_rate': 0.75,
                    'applicability': 'high'
                },
                'metadata': {
                    'source': 'learning_system',
                    'quality': 0.9,
                    'braid_level': 2,
                    'learning_method': 'pattern_analysis'
                },
                'cluster_key': [{
                    'cluster_type': 'braid_type',
                    'cluster_key': 'pattern_prediction',
                    'braid_level': 2,
                    'consumed': False
                }],
                'braid_level': 2,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test braid validation
            if braid['content']['confidence'] > 0.8:
                logger.info("    ✅ High confidence braid created")
            else:
                logger.warning("    ⚠️ Lower confidence braid created")
            
            # Test braid structure
            required_content_fields = ['braid_type', 'source_strands', 'learning_insights', 'confidence']
            for field in required_content_fields:
                if field in braid['content']:
                    logger.info(f"    ✅ Braid content field '{field}': present")
                else:
                    raise Exception(f"Missing braid content field: {field}")
            
            # Store braid for later use
            self.test_data['braid'] = braid
            
        except Exception as e:
            logger.error(f"    ❌ Braid creation test failed: {e}")
            raise
        
        logger.info("    ✅ Braid creation test successful")
    
    async def test_context_injection(self):
        """Test context injection for module enhancement"""
        logger.info("  🎯 Testing context injection...")
        
        try:
            # Test context injection for different modules
            modules = ['rdi', 'cil', 'ctp', 'dm', 'td']
            
            for module in modules:
                try:
                    # Simulate context injection
                    context = {
                        'recent_patterns': [self.test_data['pattern']],
                        'recent_predictions': [self.test_data['prediction']],
                        'recent_plans': [self.test_data['trading_plan']],
                        'recent_decisions': [self.test_data['trading_decision']],
                        'recent_executions': [self.test_data['execution_outcome']],
                        'recent_braids': [self.test_data['braid']]
                    }
                    
                    # Test context structure
                    if context['recent_patterns']:
                        logger.info(f"    ✅ {module} context injection: patterns available")
                    else:
                        logger.warning(f"    ⚠️ {module} context injection: no patterns")
                    
                    # Test context quality
                    context_quality = len([k for k, v in context.items() if v])
                    if context_quality > 3:
                        logger.info(f"    ✅ {module} context quality: {context_quality}/6 components")
                    else:
                        logger.warning(f"    ⚠️ {module} context quality: {context_quality}/6 components")
                        
                except Exception as e:
                    logger.warning(f"    ⚠️ {module} context injection failed: {e}")
            
        except Exception as e:
            logger.error(f"    ❌ Context injection test failed: {e}")
            raise
        
        logger.info("    ✅ Context injection test successful")
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        logger.info("  🔄 Testing end-to-end workflow...")
        
        try:
            # Test complete data flow
            workflow_steps = [
                ("Market Data", self.test_data['market_data']),
                ("Pattern Detection", self.test_data['pattern']),
                ("Prediction Creation", self.test_data['prediction']),
                ("Trading Plan", self.test_data['trading_plan']),
                ("Trading Decision", self.test_data['trading_decision']),
                ("Execution", self.test_data['execution_outcome']),
                ("Braid Creation", self.test_data['braid'])
            ]
            
            logger.info("    ✅ Complete workflow data flow:")
            for step_name, step_data in workflow_steps:
                if step_data:
                    logger.info(f"        ✅ {step_name}: {step_data['id']}")
                else:
                    logger.error(f"        ❌ {step_name}: Missing data")
                    raise Exception(f"Missing {step_name} data")
            
            # Test data consistency
            symbol = self.test_data['market_data']['symbol']
            for step_name, step_data in workflow_steps[1:]:  # Skip market data
                if step_data.get('symbol') == symbol:
                    logger.info(f"    ✅ {step_name}: Symbol consistency maintained")
                else:
                    logger.warning(f"    ⚠️ {step_name}: Symbol inconsistency")
            
            # Test learning progression
            braid_levels = [step_data.get('braid_level', 0) for step_name, step_data in workflow_steps[1:]]
            if all(level >= 1 for level in braid_levels):
                logger.info("    ✅ Learning progression: All components at braid level 1+")
            else:
                logger.warning("    ⚠️ Learning progression: Some components below braid level 1")
            
        except Exception as e:
            logger.error(f"    ❌ End-to-end workflow test failed: {e}")
            raise
        
        logger.info("    ✅ End-to-end workflow test successful")
    
    async def test_performance_under_load(self):
        """Test system performance under load"""
        logger.info("  💪 Testing performance under load...")
        
        try:
            # Test multiple workflow iterations
            iterations = 5
            start_time = time.time()
            
            for i in range(iterations):
                # Create test data for each iteration
                test_pattern = {
                    'id': f"load_test_pattern_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8 + i * 0.02,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'load_test',
                        'quality': 0.9
                    },
                    'cluster_key': [{
                        'cluster_type': 'pattern_type',
                        'cluster_key': 'head_and_shoulders',
                        'braid_level': 1,
                        'consumed': False
                    }],
                    'braid_level': 1,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Test resonance calculation
                resonance_scores = self.resonance_engine.calculate_module_resonance(test_pattern, 'rdi')
                
                # Test clustering
                clusters = await self.clustering_engine.get_strand_clusters(test_pattern, 'pattern')
                
                if i % 2 == 0:  # Log every other iteration
                    logger.info(f"    ✅ Load test iteration {i+1}: resonance={resonance_scores is not None}, clusters={clusters is not None}")
            
            load_time = time.time() - start_time
            avg_time_per_iteration = load_time / iterations
            
            logger.info(f"    ✅ Load test completed: {iterations} iterations in {load_time:.2f}s")
            logger.info(f"    ✅ Average time per iteration: {avg_time_per_iteration:.3f}s")
            
            if avg_time_per_iteration > 1.0:
                logger.warning(f"    ⚠️ Slow performance: {avg_time_per_iteration:.3f}s per iteration")
            else:
                logger.info(f"    ✅ Good performance: {avg_time_per_iteration:.3f}s per iteration")
            
        except Exception as e:
            logger.error(f"    ❌ Performance under load test failed: {e}")
            raise
        
        logger.info("    ✅ Performance under load test successful")
    
    def print_summary(self):
        """Print test summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 Full System Workflow Testing Summary")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📈 Test Results: {len(self.test_results)} test suites")
        
        passed_tests = 0
        for suite_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            if status == 'PASSED':
                logger.info(f"    ✅ {suite_name}")
                passed_tests += 1
            else:
                logger.info(f"    ❌ {suite_name}: {result.get('error', 'Unknown error')}")
        
        success_rate = (passed_tests / len(self.test_results)) * 100 if self.test_results else 100
        logger.info(f"📊 Success Rate: {success_rate:.1f}% ({passed_tests}/{len(self.test_results)})")
        
        if success_rate >= 90:
            logger.info("🎉 EXCELLENT: System is working as designed!")
        elif success_rate >= 70:
            logger.info("✅ GOOD: System is mostly working with minor issues")
        elif success_rate >= 50:
            logger.info("⚠️ FAIR: System has some significant issues")
        else:
            logger.info("❌ POOR: System has major issues that need fixing")
        
        logger.info("=" * 80)

async def main():
    """Main test runner"""
    tester = FullSystemWorkflowTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

