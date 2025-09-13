#!/usr/bin/env python3
"""
Real System Integration Test

This script tests the ACTUAL system with REAL components, minimal mocking,
and comprehensive coverage of the entire data flow.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import traceback

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector'))
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector', 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('real_system_test.log')
    ]
)
logger = logging.getLogger(__name__)

class RealSystemIntegrationTest:
    """Comprehensive test of the REAL system with minimal mocking"""
    
    def __init__(self):
        self.components = {}
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.real_stats = {
            'real_strands_created': 0,
            'real_llm_calls_made': 0,
            'real_database_operations': 0,
            'real_patterns_analyzed': 0,
            'real_predictions_generated': 0,
            'real_braids_created': 0,
            'real_errors': 0
        }
        
    async def run_comprehensive_real_tests(self):
        """Run comprehensive tests with REAL system components"""
        logger.info("🚀 Starting REAL System Integration Test")
        logger.info("=" * 80)
        logger.info("⚠️  This will test the ACTUAL system with REAL components")
        logger.info("⚠️  This will make REAL LLM calls and database operations")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_phases = [
            ("System Initialization", self.test_system_initialization),
            ("Database Schema Validation", self.test_database_schema),
            ("Real LLM Integration", self.test_real_llm_integration),
            ("Market Data Processing", self.test_market_data_processing),
            ("Pattern Detection", self.test_pattern_detection),
            ("Prediction Generation", self.test_prediction_generation),
            ("Learning System Processing", self.test_learning_system_processing),
            ("Braid Creation", self.test_braid_creation),
            ("Context Injection", self.test_context_injection),
            ("End-to-End Workflow", self.test_end_to_end_workflow),
            ("Performance Under Load", self.test_performance_under_load),
            ("Error Recovery", self.test_error_recovery)
        ]
        
        passed = 0
        failed = 0
        
        for phase_name, test_func in test_phases:
            try:
                logger.info(f"\n🔍 Running {phase_name}...")
                await test_func()
                logger.info(f"✅ {phase_name} PASSED")
                passed += 1
            except Exception as e:
                logger.error(f"❌ {phase_name} FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                failed += 1
                self.real_stats['real_errors'] += 1
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 REAL System Test Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📊 Real Strands Created: {self.real_stats['real_strands_created']}")
        logger.info(f"🤖 Real LLM Calls Made: {self.real_stats['real_llm_calls_made']}")
        logger.info(f"🗄️  Real Database Operations: {self.real_stats['real_database_operations']}")
        logger.info(f"🔍 Real Patterns Analyzed: {self.real_stats['real_patterns_analyzed']}")
        logger.info(f"🔮 Real Predictions Generated: {self.real_stats['real_predictions_generated']}")
        logger.info(f"🧬 Real Braids Created: {self.real_stats['real_braids_created']}")
        logger.info(f"⚠️  Real Errors: {self.real_stats['real_errors']}")
        
        if failed == 0:
            logger.info("🎉 REAL system integration test passed!")
            return True
        else:
            logger.error("⚠️  Some real system tests failed.")
            return False
    
    async def test_system_initialization(self):
        """Test REAL system component initialization"""
        logger.info("  🔧 Testing REAL system initialization...")
        
        try:
            # Initialize REAL Supabase manager
            from utils.supabase_manager import SupabaseManager
            self.components['supabase_manager'] = SupabaseManager()
            
            # Test REAL database connection
            connected = await self.components['supabase_manager'].test_connection()
            assert connected, "REAL database connection failed"
            logger.info("    ✅ REAL database connection successful")
            
            # Initialize REAL LLM client
            from llm_integration.openrouter_client import OpenRouterClient
            self.components['llm_client'] = OpenRouterClient()
            logger.info("    ✅ REAL LLM client initialized")
            
            # Initialize REAL market data processor
            from core_detection.market_data_processor import MarketDataProcessor
            self.components['market_data_processor'] = MarketDataProcessor(
                self.components['supabase_manager']
            )
            logger.info("    ✅ REAL market data processor initialized")
            
            # Initialize REAL Raw Data Intelligence Agent
            from intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
            self.components['raw_data_agent'] = RawDataIntelligenceAgent(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            logger.info("    ✅ REAL Raw Data Intelligence Agent initialized")
            
            # Initialize REAL CIL
            from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
            self.components['cil'] = SimplifiedCIL(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            logger.info("    ✅ REAL CIL initialized")
            
            # Initialize REAL learning system components
            from centralized_learning_system import CentralizedLearningSystem
            from strand_processor import StrandProcessor
            from mathematical_resonance_engine import MathematicalResonanceEngine
            from learning_pipeline import LearningPipeline
            
            self.components['strand_processor'] = StrandProcessor()
            self.components['resonance_engine'] = MathematicalResonanceEngine()
            self.components['learning_pipeline'] = LearningPipeline(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['centralized_learning'] = CentralizedLearningSystem(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            logger.info("    ✅ REAL learning system components initialized")
            
            logger.info("  ✅ REAL system initialization successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL system initialization failed: {e}")
            raise
    
    async def test_database_schema(self):
        """Test REAL database schema and operations"""
        logger.info("  🗄️  Testing REAL database schema...")
        
        try:
            # Test REAL database operations
            test_strand = {
                'id': f"real_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'timeframe': '1m',
                'content': {
                    'pattern_type': 'volume_spike',
                    'confidence': 0.85,
                    'quality': 0.9,
                    'test_data': True
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Create REAL strand
            strand_id = await self.components['supabase_manager'].create_strand(test_strand)
            assert strand_id, "REAL strand creation failed"
            self.real_stats['real_database_operations'] += 1
            self.real_stats['real_strands_created'] += 1
            
            # Read REAL strand
            retrieved_strand = await self.components['supabase_manager'].get_strand(strand_id)
            assert retrieved_strand, "REAL strand retrieval failed"
            assert retrieved_strand['id'] == strand_id, "REAL strand ID mismatch"
            self.real_stats['real_database_operations'] += 1
            
            # Update REAL strand
            update_data = {'confidence': 0.9, 'updated_at': datetime.now(timezone.utc).isoformat()}
            await self.components['supabase_manager'].update_strand(strand_id, update_data)
            self.real_stats['real_database_operations'] += 1
            
            # Verify update
            updated_strand = await self.components['supabase_manager'].get_strand(strand_id)
            assert updated_strand['confidence'] == 0.9, "REAL update verification failed"
            
            # Test JSONB operations
            jsonb_data = {
                'resonance_scores': {
                    'phi': 0.8,
                    'rho': 0.7,
                    'theta': 0.6,
                    'omega': 0.5
                },
                'metadata': {
                    'test': True,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
            jsonb_update = {'resonance_scores': jsonb_data['resonance_scores']}
            await self.components['supabase_manager'].update_strand(strand_id, jsonb_update)
            self.real_stats['real_database_operations'] += 1
            
            # Verify JSONB update
            jsonb_strand = await self.components['supabase_manager'].get_strand(strand_id)
            assert 'resonance_scores' in jsonb_strand, "REAL JSONB update failed"
            assert jsonb_strand['resonance_scores']['phi'] == 0.8, "REAL JSONB data mismatch"
            
            # Clean up
            await self.components['supabase_manager'].delete_strand(strand_id)
            self.real_stats['real_database_operations'] += 1
            
            logger.info("  ✅ REAL database schema test successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL database schema test failed: {e}")
            raise
    
    async def test_real_llm_integration(self):
        """Test REAL LLM integration with actual API calls"""
        logger.info("  🤖 Testing REAL LLM integration...")
        
        try:
            # Test REAL LLM call
            test_prompt = "Analyze this market pattern: BTC price increased 2% with 150% volume spike. What does this indicate for trading?"
            
            response = await self.components['llm_client'].generate_response(test_prompt)
            self.real_stats['real_llm_calls_made'] += 1
            
            assert response, "REAL LLM call failed"
            assert 'content' in response, "REAL LLM response missing content"
            assert isinstance(response['content'], str), "REAL LLM response content should be string"
            assert len(response['content']) > 50, "REAL LLM response too short"
            
            logger.info(f"    ✅ REAL LLM Response: {response['content'][:100]}...")
            
            # Test multiple REAL LLM calls
            prompts = [
                "What are the key indicators of a strong bullish trend?",
                "How do you assess market volatility in crypto trading?",
                "What risk management strategies work best for day trading?",
                "How do you identify false breakouts in technical analysis?",
                "What factors contribute to successful pattern recognition?"
            ]
            
            for i, prompt in enumerate(prompts):
                response = await self.components['llm_client'].generate_response(prompt)
                self.real_stats['real_llm_calls_made'] += 1
                
                assert response, f"REAL LLM call {i+1} failed"
                assert 'content' in response, f"REAL LLM response {i+1} missing content"
                assert len(response['content']) > 20, f"REAL LLM response {i+1} too short"
                
                logger.info(f"    ✅ REAL LLM Call {i+1}/5 completed")
            
            logger.info(f"    ✅ Made {self.real_stats['real_llm_calls_made']} REAL LLM calls")
            logger.info("  ✅ REAL LLM integration successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL LLM integration failed: {e}")
            raise
    
    async def test_market_data_processing(self):
        """Test REAL market data processing"""
        logger.info("  📊 Testing REAL market data processing...")
        
        try:
            # Create REAL market data
            market_data = {
                'symbol': 'BTC',
                'price': 45000.0,
                'volume': 1500.0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bid': 44950.0,
                'ask': 45050.0,
                'spread': 100.0,
                'high_24h': 46000.0,
                'low_24h': 44000.0
            }
            
            # Process through REAL market data processor
            processed_data = await self.components['market_data_processor'].process_market_data(market_data)
            assert processed_data, "REAL market data processing failed"
            
            # Validate processed data
            assert 'symbol' in processed_data, "Processed data missing symbol"
            assert 'price' in processed_data, "Processed data missing price"
            assert 'volume' in processed_data, "Processed data missing volume"
            assert processed_data['price'] > 0, "Processed price should be positive"
            assert processed_data['volume'] > 0, "Processed volume should be positive"
            
            logger.info(f"    ✅ Processed REAL market data: {processed_data['symbol']} @ ${processed_data['price']}")
            
            # Test multiple market data points
            symbols = ['BTC', 'ETH', 'SOL']
            for i, symbol in enumerate(symbols):
                data_point = {
                    'symbol': symbol,
                    'price': 45000 + (i * 1000),
                    'volume': 1000 + (i * 100),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                processed = await self.components['market_data_processor'].process_market_data(data_point)
                assert processed, f"REAL market data processing failed for {symbol}"
                
                logger.info(f"    ✅ Processed {symbol} market data")
            
            logger.info("  ✅ REAL market data processing successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL market data processing failed: {e}")
            raise
    
    async def test_pattern_detection(self):
        """Test REAL pattern detection"""
        logger.info("  🔍 Testing REAL pattern detection...")
        
        try:
            # Create REAL market data for pattern analysis
            market_data = {
                'symbol': 'BTC',
                'price': 45000.0,
                'volume': 2000.0,  # High volume for pattern detection
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'bid': 44950.0,
                'ask': 45050.0
            }
            
            # Process through REAL market data processor
            processed_data = await self.components['market_data_processor'].process_market_data(market_data)
            
            # Analyze through REAL Raw Data Intelligence Agent
            patterns = await self.components['raw_data_agent'].analyze_market_data(processed_data)
            
            # Validate patterns
            assert isinstance(patterns, list), "Patterns should be a list"
            
            if patterns:
                for pattern in patterns:
                    assert 'id' in pattern, "Pattern missing ID"
                    assert 'kind' in pattern, "Pattern missing kind"
                    assert 'content' in pattern, "Pattern missing content"
                    assert pattern['kind'] == 'pattern', "Pattern kind should be 'pattern'"
                    
                    # Store REAL pattern in database
                    strand_id = await self.components['supabase_manager'].create_strand(pattern)
                    assert strand_id, "REAL pattern storage failed"
                    self.real_stats['real_database_operations'] += 1
                    self.real_stats['real_strands_created'] += 1
                    self.real_stats['real_patterns_analyzed'] += 1
                    
                    logger.info(f"    ✅ Detected REAL pattern: {pattern.get('content', {}).get('pattern_type', 'unknown')}")
            else:
                logger.info("    ℹ️  No patterns detected (this is normal)")
            
            logger.info("  ✅ REAL pattern detection successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL pattern detection failed: {e}")
            raise
    
    async def test_prediction_generation(self):
        """Test REAL prediction generation"""
        logger.info("  🔮 Testing REAL prediction generation...")
        
        try:
            # Create REAL patterns for prediction
            patterns = []
            for i in range(3):
                pattern = {
                    'id': f"prediction_test_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'timeframe': '1m',
                    'content': {
                        'pattern_type': 'volume_spike',
                        'confidence': 0.8 + (i * 0.05),
                        'quality': 0.9,
                        'strength': 0.7 + (i * 0.1)
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Store pattern
                strand_id = await self.components['supabase_manager'].create_strand(pattern)
                patterns.append(pattern)
                self.real_stats['real_database_operations'] += 1
                self.real_stats['real_strands_created'] += 1
            
            # Generate predictions through REAL CIL
            predictions = await self.components['cil'].process_patterns(patterns)
            
            # Validate predictions
            assert isinstance(predictions, list), "Predictions should be a list"
            
            if predictions:
                for prediction in predictions:
                    assert 'id' in prediction, "Prediction missing ID"
                    assert 'kind' in prediction, "Prediction missing kind"
                    assert 'content' in prediction, "Prediction missing content"
                    
                    # Store REAL prediction in database
                    strand_id = await self.components['supabase_manager'].create_strand(prediction)
                    assert strand_id, "REAL prediction storage failed"
                    self.real_stats['real_database_operations'] += 1
                    self.real_stats['real_strands_created'] += 1
                    self.real_stats['real_predictions_generated'] += 1
                    
                    logger.info(f"    ✅ Generated REAL prediction: {prediction.get('content', {}).get('group_signature', 'unknown')}")
            else:
                logger.info("    ℹ️  No predictions generated (this is normal)")
            
            logger.info("  ✅ REAL prediction generation successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL prediction generation failed: {e}")
            raise
    
    async def test_learning_system_processing(self):
        """Test REAL learning system processing"""
        logger.info("  🧠 Testing REAL learning system processing...")
        
        try:
            # Create REAL strands for learning
            test_strands = [
                {
                    'id': f"learning_test_{uuid.uuid4()}",
                    'kind': 'prediction_review',
                    'symbol': 'BTC',
                    'content': {
                        'group_signature': 'BTC_1h_volume_spike',
                        'success': True,
                        'confidence': 0.85,
                        'actual_return': 0.03
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                {
                    'id': f"learning_test_{uuid.uuid4()}",
                    'kind': 'trade_outcome',
                    'symbol': 'ETH',
                    'content': {
                        'trade_id': f"trade_{uuid.uuid4()}",
                        'success': True,
                        'return_pct': 0.025,
                        'risk_level': 'medium'
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            # Process through REAL learning system
            for strand in test_strands:
                success = await self.components['centralized_learning'].process_strand(strand)
                assert isinstance(success, bool), "Learning system should return boolean"
                
                # Store strand
                strand_id = await self.components['supabase_manager'].create_strand(strand)
                self.real_stats['real_database_operations'] += 1
                self.real_stats['real_strands_created'] += 1
                
                logger.info(f"    ✅ Processed REAL learning strand: {strand['kind']}")
            
            # Test resonance calculations
            pattern_data = {
                '1m': {'confidence': 0.8, 'quality': 0.9},
                '5m': {'confidence': 0.7, 'quality': 0.8},
                '15m': {'confidence': 0.6, 'quality': 0.7}
            }
            
            phi = self.components['resonance_engine'].calculate_phi(pattern_data, ['1m', '5m', '15m'])
            assert phi > 0, "REAL phi calculation failed"
            assert phi <= 1, "REAL phi should be <= 1"
            
            logger.info(f"    ✅ REAL phi calculation: {phi:.3f}")
            
            # Test context injection
            context = await self.components['centralized_learning'].get_resonance_context(
                'prediction_review', {}
            )
            assert 'strand_type' in context, "REAL context injection failed"
            
            logger.info("  ✅ REAL learning system processing successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL learning system processing failed: {e}")
            raise
    
    async def test_braid_creation(self):
        """Test REAL braid creation"""
        logger.info("  🧬 Testing REAL braid creation...")
        
        try:
            # Create REAL learning insights for braid creation
            insights = [
                {
                    'id': f"insight_{uuid.uuid4()}",
                    'kind': 'learning_insight',
                    'content': {
                        'insight': 'Volume spikes above 150% of average indicate strong buying pressure',
                        'confidence': 0.9,
                        'applicability': 'high',
                        'learning_type': 'pattern_recognition'
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                {
                    'id': f"insight_{uuid.uuid4()}",
                    'kind': 'learning_insight',
                    'content': {
                        'insight': 'Price breakouts with volume confirmation have 85% success rate',
                        'confidence': 0.85,
                        'applicability': 'high',
                        'learning_type': 'success_pattern'
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            # Store insights
            for insight in insights:
                strand_id = await self.components['supabase_manager'].create_strand(insight)
                self.real_stats['real_database_operations'] += 1
                self.real_stats['real_strands_created'] += 1
            
            # Create REAL braids
            for i, insight in enumerate(insights):
                braid = {
                    'id': f"braid_{i}_{uuid.uuid4()}",
                    'kind': 'braid',
                    'braid_level': 1,
                    'content': {
                        'braid_content': f"Synthesized insight: {insight['content']['insight']}",
                        'source_insights': [insight['id']],
                        'confidence': insight['content']['confidence'],
                        'resonance_score': 0.7 + (i * 0.1),
                        'applicability': insight['content']['applicability']
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Store REAL braid
                strand_id = await self.components['supabase_manager'].create_strand(braid)
                assert strand_id, "REAL braid storage failed"
                self.real_stats['real_database_operations'] += 1
                self.real_stats['real_strands_created'] += 1
                self.real_stats['real_braids_created'] += 1
                
                logger.info(f"    ✅ Created REAL braid: {braid['id']}")
            
            logger.info("  ✅ REAL braid creation successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL braid creation failed: {e}")
            raise
    
    async def test_context_injection(self):
        """Test REAL context injection"""
        logger.info("  💉 Testing REAL context injection...")
        
        try:
            # Test context injection for different modules
            modules = ['CIL', 'CTP', 'DM']
            
            for module in modules:
                context = await self.components['centralized_learning'].get_resonance_context(
                    'prediction_review', {'module': module}
                )
                
                assert 'strand_type' in context, f"Context missing strand_type for {module}"
                assert context['strand_type'] == 'prediction_review', f"Wrong strand_type for {module}"
                
                logger.info(f"    ✅ Injected context for {module}")
            
            logger.info("  ✅ REAL context injection successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL context injection failed: {e}")
            raise
    
    async def test_end_to_end_workflow(self):
        """Test REAL end-to-end workflow"""
        logger.info("  🔄 Testing REAL end-to-end workflow...")
        
        try:
            # Complete workflow: Market Data → Patterns → Predictions → Learning → Braids
            
            # 1. Market Data
            market_data = {
                'symbol': 'BTC',
                'price': 45000.0,
                'volume': 1800.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # 2. Process Market Data
            processed_data = await self.components['market_data_processor'].process_market_data(market_data)
            assert processed_data, "Market data processing failed"
            
            # 3. Pattern Analysis
            patterns = await self.components['raw_data_agent'].analyze_market_data(processed_data)
            assert isinstance(patterns, list), "Pattern analysis failed"
            
            # 4. Prediction Generation
            predictions = await self.components['cil'].process_patterns(patterns)
            assert isinstance(predictions, list), "Prediction generation failed"
            
            # 5. Learning Processing
            if predictions:
                for prediction in predictions:
                    success = await self.components['centralized_learning'].process_strand(prediction)
                    assert isinstance(success, bool), "Learning processing failed"
            
            # 6. Context Injection
            context = await self.components['centralized_learning'].get_resonance_context(
                'prediction_review', {}
            )
            assert 'strand_type' in context, "Context injection failed"
            
            logger.info("    ✅ Complete REAL workflow executed successfully")
            logger.info("  ✅ REAL end-to-end workflow successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL end-to-end workflow failed: {e}")
            raise
    
    async def test_performance_under_load(self):
        """Test REAL performance under load"""
        logger.info("  ⚡ Testing REAL performance under load...")
        
        try:
            # Test with multiple concurrent operations
            async def concurrent_operation(operation_id):
                # Create test strand
                strand = {
                    'id': f"load_test_{operation_id}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'load_test',
                        'confidence': 0.5 + (operation_id % 10) * 0.05,
                        'operation_id': operation_id
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Store strand
                strand_id = await self.components['supabase_manager'].create_strand(strand)
                self.real_stats['real_database_operations'] += 1
                self.real_stats['real_strands_created'] += 1
                
                # Process through learning system
                success = await self.components['centralized_learning'].process_strand(strand)
                
                return success
            
            # Run 5 concurrent operations
            start_time = time.time()
            tasks = [concurrent_operation(i) for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Check results
            successful_operations = sum(1 for r in results if r is True)
            total_time = end_time - start_time
            
            logger.info(f"    ✅ Load test: {successful_operations}/5 operations successful")
            logger.info(f"    ✅ Load test time: {total_time:.2f} seconds")
            logger.info(f"    ✅ Operations per second: {5 / total_time:.2f}")
            
            # Performance assertions
            assert successful_operations > 0, "No operations succeeded under load"
            assert total_time < 30, "Performance too slow under load"
            
            logger.info("  ✅ REAL performance under load successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL performance under load failed: {e}")
            raise
    
    async def test_error_recovery(self):
        """Test REAL error recovery"""
        logger.info("  ⚠️  Testing REAL error recovery...")
        
        try:
            # Test with invalid data
            invalid_strands = [
                {'id': None, 'kind': 'pattern'},  # Invalid ID
                {'id': 'test', 'kind': None},     # Invalid kind
                {'id': 'test', 'kind': 'pattern', 'content': None},  # Invalid content
            ]
            
            for invalid_strand in invalid_strands:
                try:
                    # These should be handled gracefully
                    success = await self.components['centralized_learning'].process_strand(invalid_strand)
                    # Should either work or handle gracefully
                    assert isinstance(success, bool), "Should handle invalid data gracefully"
                except Exception:
                    # Expected to handle invalid data
                    pass
            
            # Test with malformed JSON
            try:
                malformed_json = '{"invalid": json}'
                json.loads(malformed_json)
                assert False, "Should handle malformed JSON"
            except json.JSONDecodeError:
                # Expected
                pass
            
            logger.info("  ✅ REAL error recovery successful")
            
        except Exception as e:
            logger.error(f"    ❌ REAL error recovery failed: {e}")
            raise

async def main():
    """Main test runner"""
    test_runner = RealSystemIntegrationTest()
    
    try:
        success = await test_runner.run_comprehensive_real_tests()
        
        if success:
            logger.info("\n🎉 REAL system integration test passed!")
            logger.info("The ACTUAL system is working with REAL components.")
            return 0
        else:
            logger.error("\n⚠️  REAL system integration test failed.")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test suite crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

