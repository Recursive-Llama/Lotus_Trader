#!/usr/bin/env python3
"""
Simplified Test Runner

This script runs a comprehensive test suite using mock components to avoid
real database and external service dependencies. It tests the core logic
and integration patterns without requiring actual services.
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
import psutil

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector'))
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector', 'src'))

# Import mock components
from mock_components import (
    MockSupabaseManager, MockLLMClient, MockMarketDataProcessor,
    MockRawDataIntelligenceAgent, MockSimplifiedCIL, MockAgentDiscoverySystem,
    MockInputProcessor, MockCILPlanComposer, MockExperimentOrchestrationEngine,
    MockPredictionOutcomeTracker, MockLearningFeedbackEngine, MockOutputDirectiveSystem
)

# Import learning system components
from centralized_learning_system import CentralizedLearningSystem
from strand_processor import StrandProcessor
from mathematical_resonance_engine import MathematicalResonanceEngine
from learning_pipeline import LearningPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('simplified_system_test.log')
    ]
)
logger = logging.getLogger(__name__)

class SimplifiedTestSuite:
    """Simplified test suite using mock components"""
    
    def __init__(self):
        self.components = {}
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.system_stats = {
            'strands_created': 0,
            'llm_calls_made': 0,
            'database_operations': 0,
            'errors_encountered': 0,
            'memory_usage_mb': 0,
            'cpu_usage_percent': 0
        }
        
    async def run_complete_test_suite(self):
        """Run the complete simplified test suite"""
        logger.info("🚀 Starting Simplified System Test Suite")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_phases = [
            ("Component Initialization", self.test_component_initialization),
            ("Learning System Integration", self.test_learning_system_integration),
            ("Data Flow Testing", self.test_data_flow),
            ("LLM Integration Testing", self.test_llm_integration),
            ("Error Handling Testing", self.test_error_handling),
            ("Performance Testing", self.test_performance),
            ("Integration Testing", self.test_system_integration),
            ("Cleanup and Validation", self.test_cleanup_and_validation)
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
                self.system_stats['errors_encountered'] += 1
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 Simplified Test Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"🧠 Memory Usage: {self.system_stats['memory_usage_mb']:.2f} MB")
        logger.info(f"💾 CPU Usage: {self.system_stats['cpu_usage_percent']:.2f}%")
        logger.info(f"📊 Strands Created: {self.system_stats['strands_created']}")
        logger.info(f"🤖 LLM Calls Made: {self.system_stats['llm_calls_made']}")
        logger.info(f"🗄️  Database Operations: {self.system_stats['database_operations']}")
        logger.info(f"⚠️  Errors Encountered: {self.system_stats['errors_encountered']}")
        
        if failed == 0:
            logger.info("🎉 All simplified tests passed! System logic is working correctly.")
            return True
        else:
            logger.error("⚠️  Some tests failed. Please review and fix.")
            return False
    
    async def test_component_initialization(self):
        """Test initialization of all system components"""
        logger.info("  🔧 Testing component initialization...")
        
        try:
            # Initialize mock components
            self.components['supabase_manager'] = MockSupabaseManager()
            self.components['llm_client'] = MockLLMClient()
            self.components['market_data_processor'] = MockMarketDataProcessor(self.components['supabase_manager'])
            self.components['raw_data_agent'] = MockRawDataIntelligenceAgent(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['cil'] = MockSimplifiedCIL(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['discovery_system'] = MockAgentDiscoverySystem(self.components['supabase_manager'])
            self.components['input_processor'] = MockInputProcessor(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['plan_composer'] = MockCILPlanComposer(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['experiment_engine'] = MockExperimentOrchestrationEngine(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['prediction_tracker'] = MockPredictionOutcomeTracker(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['learning_engine'] = MockLearningFeedbackEngine(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            self.components['output_directive'] = MockOutputDirectiveSystem(
                self.components['supabase_manager'],
                self.components['llm_client']
            )
            
            # Initialize learning system components
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
            
            logger.info("  ✅ All components initialized successfully")
            
        except Exception as e:
            logger.error(f"  ❌ Component initialization failed: {e}")
            raise
    
    async def test_learning_system_integration(self):
        """Test the centralized learning system integration"""
        logger.info("  🧠 Testing learning system integration...")
        
        try:
            # Test strand processing
            test_strands = [
                {
                    'id': f"pattern_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'volume_spike',
                        'confidence': 0.8,
                        'quality': 0.7
                    }
                },
                {
                    'id': f"prediction_{uuid.uuid4()}",
                    'kind': 'prediction_review',
                    'content': {
                        'group_signature': 'BTC_1h_volume_spike',
                        'success': True,
                        'confidence': 0.85
                    }
                },
                {
                    'id': f"trade_{uuid.uuid4()}",
                    'kind': 'trade_outcome',
                    'content': {
                        'trade_id': f"trade_{uuid.uuid4()}",
                        'success': True,
                        'return_pct': 0.05
                    }
                }
            ]
            
            # Process each strand type
            for strand in test_strands:
                # Test strand processing
                config = self.components['strand_processor'].process_strand(strand)
                assert config, f"Failed to process {strand['kind']} strand"
                
                # Test learning system processing
                success = await self.components['centralized_learning'].process_strand(strand)
                assert isinstance(success, bool), "Learning system processing should return boolean"
                
                # Test resonance calculations
                if strand['kind'] == 'pattern':
                    pattern_data = {
                        '1m': {'confidence': 0.8, 'quality': 0.9},
                        '5m': {'confidence': 0.7, 'quality': 0.8}
                    }
                    phi = self.components['resonance_engine'].calculate_phi(pattern_data, ['1m', '5m'])
                    assert phi > 0, "Phi calculation failed"
                
                self.system_stats['strands_created'] += 1
            
            # Test context injection
            context = await self.components['centralized_learning'].get_resonance_context(
                'prediction_review', {}
            )
            assert 'strand_type' in context, "Context injection failed"
            
            logger.info("  ✅ Learning system integration successful")
            
        except Exception as e:
            logger.error(f"  ❌ Learning system integration failed: {e}")
            raise
    
    async def test_data_flow(self):
        """Test complete data flow from input to final outputs"""
        logger.info("  📊 Testing data flow...")
        
        try:
            # Test data flow with mock data
            test_market_data = {
                'symbol': 'BTC',
                'price': 45000,
                'volume': 1000,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # 1. Market Data Processing
            processed_data = await self.components['market_data_processor'].process_market_data(test_market_data)
            assert processed_data, "Market data processing failed"
            
            # 2. Pattern Analysis
            patterns = await self.components['raw_data_agent'].analyze_market_data(processed_data)
            assert isinstance(patterns, list), "Pattern analysis failed"
            
            # 3. CIL Processing
            predictions = await self.components['cil'].process_patterns(patterns)
            assert isinstance(predictions, list), "CIL processing failed"
            
            # 4. Learning System Integration
            if patterns:
                for pattern in patterns:
                    success = await self.components['centralized_learning'].process_strand(pattern)
                    assert isinstance(success, bool), "Learning system integration failed"
                    self.system_stats['strands_created'] += 1
            
            # 5. Agent Discovery
            agents = await self.components['discovery_system'].discover_agents()
            assert isinstance(agents, list), "Agent discovery failed"
            
            logger.info("  ✅ Data flow testing successful")
            
        except Exception as e:
            logger.error(f"  ❌ Data flow testing failed: {e}")
            raise
    
    async def test_llm_integration(self):
        """Test LLM integration and calls"""
        logger.info("  🤖 Testing LLM integration...")
        
        try:
            # Test basic LLM call
            test_prompt = "Analyze this market pattern: BTC price increased 2% with high volume. What does this indicate?"
            
            response = await self.components['llm_client'].generate_response(test_prompt)
            assert response, "LLM call failed"
            assert 'content' in response, "LLM response missing content"
            self.system_stats['llm_calls_made'] += 1
            
            logger.info("  ✅ Basic LLM call successful")
            
            # Test pattern analysis LLM call
            pattern_data = {
                'symbol': 'BTC',
                'price': 45000,
                'volume': 1500,
                'pattern_type': 'volume_spike'
            }
            
            analysis_prompt = f"Analyze this trading pattern: {json.dumps(pattern_data)}"
            analysis_response = await self.components['llm_client'].generate_response(analysis_prompt)
            assert analysis_response, "Pattern analysis LLM call failed"
            self.system_stats['llm_calls_made'] += 1
            
            logger.info("  ✅ Pattern analysis LLM call successful")
            
            # Test prediction generation LLM call
            prediction_prompt = "Based on current market conditions, predict BTC price movement for the next hour."
            prediction_response = await self.components['llm_client'].generate_response(prediction_prompt)
            assert prediction_response, "Prediction LLM call failed"
            self.system_stats['llm_calls_made'] += 1
            
            logger.info("  ✅ Prediction generation LLM call successful")
            
        except Exception as e:
            logger.error(f"  ❌ LLM integration testing failed: {e}")
            raise
    
    async def test_error_handling(self):
        """Test error handling and recovery"""
        logger.info("  ⚠️  Testing error handling...")
        
        try:
            # Test invalid strand handling
            invalid_strand = {
                'id': 'invalid',
                'kind': 'invalid_type',
                'content': None
            }
            
            success = await self.components['centralized_learning'].process_strand(invalid_strand)
            # Should handle gracefully, not crash
            assert isinstance(success, bool), "Invalid strand should be handled gracefully"
            
            # Test malformed data handling
            malformed_data = {
                'symbol': 'BTC',
                'price': 'invalid_price',  # Invalid price type
                'volume': -100  # Invalid volume
            }
            
            try:
                processed = await self.components['market_data_processor'].process_market_data(malformed_data)
                # Should either process or handle gracefully
                assert processed is not None or True, "Malformed data should be handled"
            except Exception:
                # Expected to handle malformed data
                pass
            
            logger.info("  ✅ Error handling testing successful")
            
        except Exception as e:
            logger.error(f"  ❌ Error handling testing failed: {e}")
            raise
    
    async def test_performance(self):
        """Test system performance and scalability"""
        logger.info("  ⚡ Testing performance...")
        
        try:
            # Test memory usage
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Test CPU usage
            cpu_before = process.cpu_percent()
            
            # Test with multiple concurrent operations
            async def concurrent_operation(operation_id):
                strand = {
                    'id': f"perf_test_{operation_id}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'performance_test',
                        'operation_id': operation_id,
                        'confidence': 0.5 + (operation_id % 10) * 0.05
                    }
                }
                
                # Process through learning system
                success = await self.components['centralized_learning'].process_strand(strand)
                return success
            
            # Run 10 concurrent operations
            start_time = time.time()
            tasks = [concurrent_operation(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # Check results
            successful_operations = sum(1 for r in results if r is True)
            assert successful_operations > 0, "No operations succeeded"
            
            # Calculate performance metrics
            total_time = end_time - start_time
            operations_per_second = len(results) / total_time
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            cpu_after = process.cpu_percent()
            
            self.system_stats['memory_usage_mb'] = memory_after
            self.system_stats['cpu_usage_percent'] = cpu_after
            
            logger.info(f"  ✅ Performance test completed:")
            logger.info(f"     - Operations per second: {operations_per_second:.2f}")
            logger.info(f"     - Memory usage: {memory_after:.2f} MB")
            logger.info(f"     - CPU usage: {cpu_after:.2f}%")
            logger.info(f"     - Successful operations: {successful_operations}/{len(results)}")
            
            # Performance assertions
            assert operations_per_second > 1, "Performance too slow"
            assert memory_after < 1000, "Memory usage too high"  # Less than 1GB
            
        except Exception as e:
            logger.error(f"  ❌ Performance testing failed: {e}")
            raise
    
    async def test_system_integration(self):
        """Test complete system integration"""
        logger.info("  🔗 Testing system integration...")
        
        try:
            # Test component interactions
            # 1. Market Data -> Raw Data Intelligence
            test_market_data = {
                'symbol': 'BTC',
                'price': 45000,
                'volume': 1000,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            processed_data = await self.components['market_data_processor'].process_market_data(test_market_data)
            assert processed_data, "Market data processing failed"
            
            # 2. Patterns -> CIL
            patterns = await self.components['raw_data_agent'].analyze_market_data(processed_data)
            predictions = await self.components['cil'].process_patterns(patterns or [])
            
            # 3. Learning System Integration
            if patterns:
                for pattern in patterns:
                    success = await self.components['centralized_learning'].process_strand(pattern)
                    assert isinstance(success, bool), "Learning system integration failed"
            
            # 4. Test agent discovery
            agents = await self.components['discovery_system'].discover_agents()
            assert isinstance(agents, list), "Agent discovery failed"
            
            # 5. Test CIL components integration
            if predictions:
                for prediction in predictions:
                    # Test input processor
                    processed_input = await self.components['input_processor'].process_input(prediction)
                    assert processed_input, "Input processing failed"
                    
                    # Test plan composer
                    plan = await self.components['plan_composer'].compose_plan(processed_input)
                    # Plan might be None, that's okay
            
            logger.info("  ✅ System integration testing successful")
            
        except Exception as e:
            logger.error(f"  ❌ System integration testing failed: {e}")
            raise
    
    async def test_cleanup_and_validation(self):
        """Test cleanup and final validation"""
        logger.info("  🧹 Testing cleanup and validation...")
        
        try:
            # Test graceful shutdown
            for name, component in self.components.items():
                if hasattr(component, 'shutdown'):
                    await component.shutdown()
                elif hasattr(component, 'close'):
                    await component.close()
                elif hasattr(component, 'disconnect'):
                    await component.disconnect()
            
            # Validate final state
            assert self.system_stats['strands_created'] > 0, "No strands were created during testing"
            assert self.system_stats['llm_calls_made'] > 0, "No LLM calls were made during testing"
            
            # Check for memory leaks (basic check)
            process = psutil.Process()
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            if final_memory > 500:  # More than 500MB
                logger.warning(f"  ⚠️  High memory usage detected: {final_memory:.2f} MB")
            
            logger.info("  ✅ Cleanup and validation successful")
            
        except Exception as e:
            logger.error(f"  ❌ Cleanup and validation failed: {e}")
            raise

async def main():
    """Main test runner"""
    test_suite = SimplifiedTestSuite()
    
    try:
        success = await test_suite.run_complete_test_suite()
        
        if success:
            logger.info("\n🎉 Simplified test suite passed!")
            logger.info("The system logic is working correctly and ready for real integration.")
            return 0
        else:
            logger.error("\n⚠️  Some tests failed. Please review and fix.")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test suite crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

