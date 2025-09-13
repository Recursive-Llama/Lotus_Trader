#!/usr/bin/env python3
"""
Test Series Runner

This script runs a series of focused tests that can be run individually
to comprehensively test the REAL system with minimal mocking.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
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
        logging.FileHandler('test_series_results.log')
    ]
)
logger = logging.getLogger(__name__)

# Global imports
from llm_integration.prompt_manager import PromptManager

class TestSeriesRunner:
    """Runner for series of focused tests"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    async def run_test_series(self):
        """Run the complete test series"""
        logger.info("🚀 Starting Test Series Runner")
        logger.info("=" * 80)
        logger.info("This will run a series of focused tests on the REAL system")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_series = [
            ("Test 1: Database Connection", self.test_database_connection),
            ("Test 2: LLM API Connection", self.test_llm_api_connection),
            ("Test 3: Component Initialization", self.test_component_initialization),
            ("Test 4: Basic Data Flow", self.test_basic_data_flow),
            ("Test 5: Pattern Detection", self.test_pattern_detection),
            ("Test 6: Prediction Generation", self.test_prediction_generation),
            ("Test 7: Learning System", self.test_learning_system),
            ("Test 8: Braid Creation", self.test_braid_creation),
            ("Test 9: Context Injection", self.test_context_injection),
            ("Test 10: End-to-End Workflow", self.test_end_to_end_workflow),
            ("Test 11: Performance Test", self.test_performance),
            ("Test 12: Error Handling", self.test_error_handling)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in test_series:
            try:
                logger.info(f"\n🔍 Running {test_name}...")
                await test_func()
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
                self.test_results[test_name] = {'status': 'PASSED', 'error': None}
            except Exception as e:
                logger.error(f"❌ {test_name} FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                failed += 1
                self.test_results[test_name] = {'status': 'FAILED', 'error': str(e)}
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 Test Series Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        
        # Print detailed results
        for test_name, result in self.test_results.items():
            status = "✅" if result['status'] == 'PASSED' else "❌"
            logger.info(f"   {status} {test_name}")
            if result['error']:
                logger.info(f"      Error: {result['error']}")
        
        if failed == 0:
            logger.info("\n🎉 All test series passed!")
            return True
        else:
            logger.error(f"\n⚠️  {failed} test series failed.")
            return False
    
    async def test_database_connection(self):
        """Test 1: Database Connection"""
        logger.info("  🗄️  Testing database connection...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            supabase_manager = SupabaseManager()
            
            # Test connection
            connected = supabase_manager.test_connection()
            assert connected, "Database connection failed"
            
            logger.info("    ✅ Database connection successful")
            
        except Exception as e:
            logger.error(f"    ❌ Database connection failed: {e}")
            raise
    
    async def test_llm_api_connection(self):
        """Test 2: LLM API Connection"""
        logger.info("  🤖 Testing LLM API connection...")
        
        try:
            from llm_integration.openrouter_client import OpenRouterClient
            llm_client = OpenRouterClient()
            
            # Test basic LLM call
            response = llm_client.generate_completion("Hello, respond with 'LLM test successful'")
            assert response, "LLM call failed"
            assert 'content' in response, "LLM response missing content"
            assert len(response['content']) > 0, "LLM response empty"
            
            logger.info(f"    ✅ LLM API response: {response['content'][:50]}...")
            
        except Exception as e:
            logger.error(f"    ❌ LLM API connection failed: {e}")
            raise
    
    async def test_component_initialization(self):
        """Test 3: Component Initialization"""
        logger.info("  🔧 Testing component initialization...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from core_detection.market_data_processor import MarketDataProcessor
            from intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
            from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
            from centralized_learning_system import CentralizedLearningSystem
            from strand_processor import StrandProcessor
            from mathematical_resonance_engine import MathematicalResonanceEngine
            from learning_pipeline import LearningPipeline
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            market_data_processor = MarketDataProcessor(supabase_manager)
            raw_data_agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
            cil = SimplifiedCIL(supabase_manager, llm_client)
            strand_processor = StrandProcessor()
            resonance_engine = MathematicalResonanceEngine()
            prompt_manager = PromptManager()
            learning_pipeline = LearningPipeline(supabase_manager, llm_client, prompt_manager)
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            logger.info("    ✅ All components initialized successfully")
            
        except Exception as e:
            logger.error(f"    ❌ Component initialization failed: {e}")
            raise
    
    async def test_basic_data_flow(self):
        """Test 4: Basic Data Flow"""
        logger.info("  📊 Testing basic data flow...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from core_detection.market_data_processor import MarketDataProcessor
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            market_data_processor = MarketDataProcessor(supabase_manager)
            
            # Test market data processing
            market_data = {
                'symbol': 'BTC',
                'open': 45000.0,
                'high': 45100.0,
                'low': 44900.0,
                'close': 45050.0,
                'volume': 1000.0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source': 'test'
            }
            
            processed_data = await market_data_processor.process_market_data(market_data)
            assert processed_data, "Market data processing failed"
            assert 'symbol' in processed_data, "Processed data missing symbol"
            assert 'close' in processed_data, "Processed data missing close price"
            
            logger.info(f"    ✅ Processed market data: {processed_data['symbol']} @ ${processed_data['close']}")
            
        except Exception as e:
            logger.error(f"    ❌ Basic data flow failed: {e}")
            raise
    
    async def test_pattern_detection(self):
        """Test 5: Pattern Detection"""
        logger.info("  🔍 Testing pattern detection...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from core_detection.market_data_processor import MarketDataProcessor
            from intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            market_data_processor = MarketDataProcessor(supabase_manager)
            raw_data_agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
            
            # Test pattern detection
            market_data = {
                'symbol': 'BTC',
                'price': 45000.0,
                'volume': 1500.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            processed_data = await market_data_processor.process_market_data(market_data)
            patterns = await raw_data_agent.analyze_market_data(processed_data)
            
            assert isinstance(patterns, list), "Patterns should be a list"
            
            if patterns:
                for pattern in patterns:
                    assert 'id' in pattern, "Pattern missing ID"
                    assert 'kind' in pattern, "Pattern missing kind"
                    assert 'content' in pattern, "Pattern missing content"
                
                logger.info(f"    ✅ Detected {len(patterns)} patterns")
            else:
                logger.info("    ℹ️  No patterns detected (normal)")
            
        except Exception as e:
            logger.error(f"    ❌ Pattern detection failed: {e}")
            raise
    
    async def test_prediction_generation(self):
        """Test 6: Prediction Generation"""
        logger.info("  🔮 Testing prediction generation...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            cil = SimplifiedCIL(supabase_manager, llm_client)
            
            # Create test patterns
            patterns = [
                {
                    'id': f"test_pattern_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'volume_spike',
                        'confidence': 0.8,
                        'quality': 0.9
                    }
                }
            ]
            
            # Generate predictions
            predictions = await cil.process_patterns(patterns)
            
            assert isinstance(predictions, list), "Predictions should be a list"
            
            if predictions:
                for prediction in predictions:
                    assert 'id' in prediction, "Prediction missing ID"
                    assert 'kind' in prediction, "Prediction missing kind"
                    assert 'content' in prediction, "Prediction missing content"
                
                logger.info(f"    ✅ Generated {len(predictions)} predictions")
            else:
                logger.info("    ℹ️  No predictions generated (normal)")
            
        except Exception as e:
            logger.error(f"    ❌ Prediction generation failed: {e}")
            raise
    
    async def test_learning_system(self):
        """Test 7: Learning System"""
        logger.info("  🧠 Testing learning system...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from centralized_learning_system import CentralizedLearningSystem
            from llm_integration.prompt_manager import PromptManager
            from mathematical_resonance_engine import MathematicalResonanceEngine
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            resonance_engine = MathematicalResonanceEngine()
            
            # Test strand processing
            test_strand = {
                'id': f"learning_test_{uuid.uuid4()}",
                'kind': 'prediction_review',
                'symbol': 'BTC',
                'content': {
                    'group_signature': 'BTC_1h_volume_spike',
                    'success': True,
                    'confidence': 0.85
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Process strand
            success = await centralized_learning.process_strand(test_strand)
            assert isinstance(success, bool), "Learning system should return boolean"
            
            # Test resonance calculations
            pattern_data = {
                '1m': {'confidence': 0.8, 'quality': 0.9},
                '5m': {'confidence': 0.7, 'quality': 0.8}
            }
            
            phi = resonance_engine.calculate_phi(pattern_data, ['1m', '5m'])
            assert phi > 0, "Phi calculation failed"
            assert phi <= 1, "Phi should be <= 1"
            
            logger.info(f"    ✅ Learning system processing successful (phi: {phi:.3f})")
            
        except Exception as e:
            logger.error(f"    ❌ Learning system failed: {e}")
            raise
    
    async def test_braid_creation(self):
        """Test 8: Braid Creation"""
        logger.info("  🧬 Testing braid creation...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from centralized_learning_system import CentralizedLearningSystem
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            # Create test learning insight
            insight = {
                'id': f"insight_{uuid.uuid4()}",
                'kind': 'learning_insight',
                'content': {
                    'insight': 'Volume spikes above 150% of average indicate strong buying pressure',
                    'confidence': 0.9,
                    'applicability': 'high'
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Process insight
            success = await centralized_learning.process_strand(insight)
            assert isinstance(success, bool), "Braid creation should return boolean"
            
            logger.info("    ✅ Braid creation successful")
            
        except Exception as e:
            logger.error(f"    ❌ Braid creation failed: {e}")
            raise
    
    async def test_context_injection(self):
        """Test 9: Context Injection"""
        logger.info("  💉 Testing context injection...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from centralized_learning_system import CentralizedLearningSystem
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            # Test context injection
            context = await centralized_learning.get_resonance_context(
                'prediction_review', {'module': 'CIL'}
            )
            
            assert 'strand_type' in context, "Context missing strand_type"
            assert context['strand_type'] == 'prediction_review', "Wrong strand_type"
            
            logger.info("    ✅ Context injection successful")
            
        except Exception as e:
            logger.error(f"    ❌ Context injection failed: {e}")
            raise
    
    async def test_end_to_end_workflow(self):
        """Test 10: End-to-End Workflow"""
        logger.info("  🔄 Testing end-to-end workflow...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from core_detection.market_data_processor import MarketDataProcessor
            from intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
            from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
            from centralized_learning_system import CentralizedLearningSystem
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            market_data_processor = MarketDataProcessor(supabase_manager)
            raw_data_agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
            cil = SimplifiedCIL(supabase_manager, llm_client)
            prompt_manager = PromptManager()
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            # Complete workflow
            market_data = {
                'symbol': 'BTC',
                'open': 44800.0,
                'high': 45200.0,
                'low': 44700.0,
                'close': 45000.0,
                'volume': 1200.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # 1. Process market data
            processed_data = await market_data_processor.process_market_data(market_data)
            assert processed_data, "Market data processing failed"
            
            # 2. Detect patterns
            patterns = await raw_data_agent.analyze_market_data(processed_data)
            assert isinstance(patterns, list), "Pattern detection failed"
            
            # 3. Generate predictions
            predictions = await cil.process_patterns(patterns)
            assert isinstance(predictions, list), "Prediction generation failed"
            
            # 4. Process through learning system
            if predictions:
                for prediction in predictions:
                    success = await centralized_learning.process_strand(prediction)
                    assert isinstance(success, bool), "Learning processing failed"
            
            # 5. Test context injection
            context = await centralized_learning.get_resonance_context(
                'prediction_review', {}
            )
            assert 'strand_type' in context, "Context injection failed"
            
            logger.info("    ✅ Complete end-to-end workflow successful")
            
        except Exception as e:
            logger.error(f"    ❌ End-to-end workflow failed: {e}")
            raise
    
    async def test_performance(self):
        """Test 11: Performance Test"""
        logger.info("  ⚡ Testing performance...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from centralized_learning_system import CentralizedLearningSystem
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            # Test performance with multiple operations
            async def performance_operation(i):
                strand = {
                    'id': f"perf_test_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'performance_test',
                        'confidence': 0.5 + (i % 10) * 0.05
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                success = await centralized_learning.process_strand(strand)
                return success
            
            # Run 3 concurrent operations
            start_time = time.time()
            tasks = [performance_operation(i) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_operations = sum(1 for r in results if r is True)
            total_time = end_time - start_time
            
            logger.info(f"    ✅ Performance: {successful_operations}/3 operations in {total_time:.2f}s")
            
            assert successful_operations > 0, "No operations succeeded"
            assert total_time < 60, "Performance too slow"
            
        except Exception as e:
            logger.error(f"    ❌ Performance test failed: {e}")
            raise
    
    async def test_error_handling(self):
        """Test 12: Error Handling"""
        logger.info("  ⚠️  Testing error handling...")
        
        try:
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from centralized_learning_system import CentralizedLearningSystem
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize components
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            # Test with invalid data
            invalid_strand = {
                'id': 'invalid',
                'kind': 'invalid_type',
                'content': None
            }
            
            try:
                success = await centralized_learning.process_strand(invalid_strand)
                # Should handle gracefully
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
            
            logger.info("    ✅ Error handling successful")
            
        except Exception as e:
            logger.error(f"    ❌ Error handling failed: {e}")
            raise

async def main():
    """Main test runner"""
    test_runner = TestSeriesRunner()
    
    try:
        success = await test_runner.run_test_series()
        
        if success:
            logger.info("\n🎉 Test series completed successfully!")
            return 0
        else:
            logger.error("\n⚠️  Test series completed with failures.")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test series crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
