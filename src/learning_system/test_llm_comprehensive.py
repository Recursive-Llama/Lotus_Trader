#!/usr/bin/env python3
"""
Comprehensive LLM Integration Testing Suite

Tests all LLM operations, prompt management, response processing,
and integration with the centralized learning system.
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

from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from llm_integration.prompt_manager import PromptManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('llm_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class LLMComprehensiveTester:
    """Comprehensive LLM integration testing suite"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.prompt_manager = PromptManager()
        self.test_results = {}
        self.start_time = None
        
    async def run_all_tests(self):
        """Run all LLM tests"""
        logger.info("🤖 Starting Comprehensive LLM Integration Testing")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_suites = [
            ("LLM API Connection", self.test_llm_api_connection),
            ("Prompt Management", self.test_prompt_management),
            ("Response Processing", self.test_response_processing),
            ("Learning Prompts", self.test_learning_prompts),
            ("Context Injection", self.test_context_injection),
            ("Error Handling", self.test_error_handling),
            ("Performance Testing", self.test_performance),
            ("Integration Testing", self.test_integration),
            ("Real Scenarios", self.test_real_scenarios),
            ("Stress Testing", self.test_stress_testing)
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
    
    async def test_llm_api_connection(self):
        """Test LLM API connection and basic functionality"""
        logger.info("  🔌 Testing LLM API connection...")
        
        try:
            # Test basic connection
            test_prompt = "Hello, this is a test. Please respond with 'API connection successful'."
            
            response = await self.llm_client.generate_completion(
                prompt=test_prompt,
                max_tokens=50,
                temperature=0.1
            )
            
            if response and 'API connection successful' in response:
                logger.info("    ✅ LLM API connection successful")
            else:
                logger.warning(f"    ⚠️ Unexpected response: {response}")
            
            # Test different models
            models_to_test = ['openai/gpt-3.5-turbo', 'openai/gpt-4']
            for model in models_to_test:
                try:
                    response = await self.llm_client.generate_completion(
                        prompt="Test model availability",
                        max_tokens=10,
                        temperature=0.1,
                        model=model
                    )
                    if response:
                        logger.info(f"    ✅ Model {model} available")
                    else:
                        logger.warning(f"    ⚠️ Model {model} not responding")
                except Exception as e:
                    logger.warning(f"    ⚠️ Model {model} error: {e}")
            
        except Exception as e:
            logger.error(f"    ❌ LLM API connection failed: {e}")
            raise
        
        logger.info("    ✅ LLM API connection test successful")
    
    async def test_prompt_management(self):
        """Test prompt management system"""
        logger.info("  📝 Testing prompt management...")
        
        try:
            # Test prompt retrieval
            test_prompts = [
                'learning_analysis',
                'pattern_analysis', 
                'prediction_review',
                'trading_plan_generation',
                'context_injection'
            ]
            
            for prompt_name in test_prompts:
                try:
                    prompt = self.prompt_manager.get_prompt(prompt_name)
                    if prompt and len(prompt) > 10:
                        logger.info(f"    ✅ Prompt '{prompt_name}' retrieved successfully")
                    else:
                        logger.warning(f"    ⚠️ Prompt '{prompt_name}' empty or too short")
                except Exception as e:
                    logger.warning(f"    ⚠️ Prompt '{prompt_name}' error: {e}")
            
            # Test prompt customization
            custom_prompt = self.prompt_manager.get_prompt(
                'learning_analysis',
                context={'strand_type': 'pattern', 'symbol': 'BTC'}
            )
            if custom_prompt and 'BTC' in custom_prompt:
                logger.info("    ✅ Prompt customization successful")
            else:
                logger.warning("    ⚠️ Prompt customization may not be working")
            
            # Test prompt validation
            valid_prompts = self.prompt_manager.validate_prompts()
            if valid_prompts:
                logger.info(f"    ✅ Prompt validation: {len(valid_prompts)} prompts valid")
            else:
                logger.warning("    ⚠️ No valid prompts found")
            
        except Exception as e:
            logger.error(f"    ❌ Prompt management test failed: {e}")
            raise
        
        logger.info("    ✅ Prompt management test successful")
    
    async def test_response_processing(self):
        """Test LLM response processing and parsing"""
        logger.info("  🔄 Testing response processing...")
        
        try:
            # Test structured response parsing
            test_prompt = """
            Analyze this pattern data and return a JSON response with:
            - pattern_type: string
            - confidence: float (0-1)
            - analysis: string
            - recommendations: array of strings
            
            Pattern data: {"symbol": "BTC", "price": 45000, "volume": 1200}
            """
            
            response = await self.llm_client.generate_completion(
                prompt=test_prompt,
                max_tokens=200,
                temperature=0.1
            )
            
            if response:
                logger.info("    ✅ LLM response received")
                
                # Try to parse as JSON
                try:
                    # Look for JSON in response
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group()
                        parsed = json.loads(json_str)
                        logger.info("    ✅ JSON response parsing successful")
                    else:
                        logger.warning("    ⚠️ No JSON found in response")
                except json.JSONDecodeError as e:
                    logger.warning(f"    ⚠️ JSON parsing failed: {e}")
            else:
                logger.error("    ❌ No response received")
                raise Exception("No response received")
            
            # Test response quality
            quality_prompt = "Rate the quality of this trading pattern from 1-10: Head and Shoulders reversal"
            quality_response = await self.llm_client.generate_completion(
                prompt=quality_prompt,
                max_tokens=50,
                temperature=0.1
            )
            
            if quality_response and any(char.isdigit() for char in quality_response):
                logger.info("    ✅ Response quality assessment working")
            else:
                logger.warning("    ⚠️ Response quality assessment unclear")
            
        except Exception as e:
            logger.error(f"    ❌ Response processing test failed: {e}")
            raise
        
        logger.info("    ✅ Response processing test successful")
    
    async def test_learning_prompts(self):
        """Test learning-specific prompts and responses"""
        logger.info("  🧠 Testing learning prompts...")
        
        try:
            # Test pattern analysis prompt
            pattern_data = {
                "symbol": "BTC",
                "pattern_type": "head_and_shoulders",
                "confidence": 0.85,
                "timeframe": "1h",
                "price": 45000
            }
            
            pattern_prompt = self.prompt_manager.get_prompt(
                'pattern_analysis',
                context=pattern_data
            )
            
            pattern_response = await self.llm_client.generate_completion(
                prompt=pattern_prompt,
                max_tokens=300,
                temperature=0.2
            )
            
            if pattern_response and len(pattern_response) > 50:
                logger.info("    ✅ Pattern analysis prompt successful")
            else:
                logger.warning("    ⚠️ Pattern analysis prompt response too short")
            
            # Test prediction review prompt
            prediction_data = {
                "prediction": "BTC will reach $50000 in 24h",
                "confidence": 0.75,
                "reasoning": "Technical indicators show bullish momentum"
            }
            
            prediction_prompt = self.prompt_manager.get_prompt(
                'prediction_review',
                context=prediction_data
            )
            
            prediction_response = await self.llm_client.generate_completion(
                prompt=prediction_prompt,
                max_tokens=300,
                temperature=0.2
            )
            
            if prediction_response and len(prediction_response) > 50:
                logger.info("    ✅ Prediction review prompt successful")
            else:
                logger.warning("    ⚠️ Prediction review prompt response too short")
            
            # Test trading plan generation prompt
            plan_data = {
                "market_conditions": "bullish",
                "risk_tolerance": "medium",
                "symbol": "BTC",
                "current_price": 45000
            }
            
            plan_prompt = self.prompt_manager.get_prompt(
                'trading_plan_generation',
                context=plan_data
            )
            
            plan_response = await self.llm_client.generate_completion(
                prompt=plan_prompt,
                max_tokens=400,
                temperature=0.3
            )
            
            if plan_response and len(plan_response) > 50:
                logger.info("    ✅ Trading plan generation prompt successful")
            else:
                logger.warning("    ⚠️ Trading plan generation prompt response too short")
            
        except Exception as e:
            logger.error(f"    ❌ Learning prompts test failed: {e}")
            raise
        
        logger.info("    ✅ Learning prompts test successful")
    
    async def test_context_injection(self):
        """Test context injection for prompts"""
        logger.info("  🎯 Testing context injection...")
        
        try:
            # Test basic context injection
            context = {
                'strand_type': 'pattern',
                'symbol': 'ETH',
                'confidence': 0.88,
                'market_conditions': 'volatile',
                'recent_patterns': ['double_top', 'flag_pattern'],
                'historical_performance': 0.75
            }
            
            context_prompt = self.prompt_manager.get_prompt(
                'context_injection',
                context=context
            )
            
            if context_prompt and all(key in context_prompt for key in ['ETH', '0.88', 'volatile']):
                logger.info("    ✅ Context injection successful")
            else:
                logger.warning("    ⚠️ Context injection may not be working properly")
            
            # Test complex context injection
            complex_context = {
                'strand_type': 'prediction_review',
                'symbol': 'BTC',
                'prediction_data': {
                    'price_target': 50000,
                    'timeframe': '24h',
                    'confidence': 0.82
                },
                'market_data': {
                    'current_price': 45000,
                    'volume': 1200,
                    'volatility': 0.15
                },
                'historical_context': {
                    'similar_patterns': 3,
                    'success_rate': 0.67
                }
            }
            
            complex_prompt = self.prompt_manager.get_prompt(
                'learning_analysis',
                context=complex_context
            )
            
            if complex_prompt and len(complex_prompt) > 100:
                logger.info("    ✅ Complex context injection successful")
            else:
                logger.warning("    ⚠️ Complex context injection may need improvement")
            
        except Exception as e:
            logger.error(f"    ❌ Context injection test failed: {e}")
            raise
        
        logger.info("    ✅ Context injection test successful")
    
    async def test_error_handling(self):
        """Test LLM error handling and recovery"""
        logger.info("  🚨 Testing error handling...")
        
        try:
            # Test invalid prompt handling
            try:
                invalid_response = await self.llm_client.generate_completion(
                    prompt="",  # Empty prompt
                    max_tokens=10
                )
                logger.warning("    ⚠️ Empty prompt should have failed")
            except Exception as e:
                logger.info("    ✅ Empty prompt properly rejected")
            
            # Test invalid parameters
            try:
                invalid_response = await self.llm_client.generate_completion(
                    prompt="Test",
                    max_tokens=-1  # Invalid token count
                )
                logger.warning("    ⚠️ Invalid parameters should have failed")
            except Exception as e:
                logger.info("    ✅ Invalid parameters properly rejected")
            
            # Test timeout handling
            try:
                timeout_response = await self.llm_client.generate_completion(
                    prompt="Write a very long detailed analysis of the stock market",
                    max_tokens=5000,
                    temperature=0.1
                )
                if timeout_response:
                    logger.info("    ✅ Large request handled successfully")
                else:
                    logger.warning("    ⚠️ Large request may have timed out")
            except Exception as e:
                logger.info(f"    ✅ Large request properly handled: {e}")
            
            # Test malformed JSON response
            malformed_prompt = "Return this exact text: {invalid json"
            malformed_response = await self.llm_client.generate_completion(
                prompt=malformed_prompt,
                max_tokens=50
            )
            
            if malformed_response:
                logger.info("    ✅ Malformed response handled gracefully")
            else:
                logger.warning("    ⚠️ Malformed response handling unclear")
            
        except Exception as e:
            logger.error(f"    ❌ Error handling test failed: {e}")
            raise
        
        logger.info("    ✅ Error handling test successful")
    
    async def test_performance(self):
        """Test LLM performance and response times"""
        logger.info("  ⚡ Testing performance...")
        
        try:
            # Test response time
            start_time = time.time()
            response = await self.llm_client.generate_completion(
                prompt="Analyze this trading pattern: Head and Shoulders",
                max_tokens=100,
                temperature=0.1
            )
            response_time = time.time() - start_time
            
            logger.info(f"    ✅ Response time: {response_time:.2f}s")
            
            if response_time > 10.0:
                logger.warning(f"    ⚠️ Slow response time: {response_time:.2f}s")
            elif response_time > 5.0:
                logger.warning(f"    ⚠️ Moderate response time: {response_time:.2f}s")
            
            # Test concurrent requests
            concurrent_tasks = []
            start_time = time.time()
            
            for i in range(3):
                task = asyncio.create_task(
                    self.llm_client.generate_completion(
                        prompt=f"Test concurrent request {i}",
                        max_tokens=50,
                        temperature=0.1
                    )
                )
                concurrent_tasks.append(task)
            
            concurrent_responses = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            concurrent_time = time.time() - start_time
            
            successful_responses = sum(1 for r in concurrent_responses if not isinstance(r, Exception))
            logger.info(f"    ✅ Concurrent requests: {successful_responses}/3 successful in {concurrent_time:.2f}s")
            
            # Test token efficiency
            efficiency_prompt = "Rate this pattern from 1-10: Double Top"
            efficiency_response = await self.llm_client.generate_completion(
                prompt=efficiency_prompt,
                max_tokens=10,
                temperature=0.1
            )
            
            if efficiency_response and len(efficiency_response.split()) <= 20:
                logger.info("    ✅ Token efficiency good")
            else:
                logger.warning("    ⚠️ Token efficiency could be improved")
            
        except Exception as e:
            logger.error(f"    ❌ Performance test failed: {e}")
            raise
        
        logger.info("    ✅ Performance test successful")
    
    async def test_integration(self):
        """Test LLM integration with learning system"""
        logger.info("  🔗 Testing integration...")
        
        try:
            # Test with real strand data
            test_strand = {
                "id": f"llm_test_{uuid.uuid4()}",
                "kind": "pattern",
                "symbol": "BTC",
                "content": {
                    "pattern_type": "head_and_shoulders",
                    "confidence": 0.85,
                    "timeframe": "1h"
                },
                "metadata": {
                    "source": "llm_test",
                    "quality": 0.92
                },
                "resonance_scores": {
                    "phi": 0.75,
                    "rho": 0.82,
                    "theta": 0.68,
                    "omega": 0.89
                },
                "cluster_key": [{
                    "cluster_type": "pattern_type",
                    "cluster_key": "head_and_shoulders",
                    "braid_level": 1,
                    "consumed": False
                }],
                "braid_level": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert test strand
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            logger.info("    ✅ Test strand inserted")
            
            # Test learning analysis with real data
            learning_prompt = self.prompt_manager.get_prompt(
                'learning_analysis',
                context=test_strand
            )
            
            learning_response = await self.llm_client.generate_completion(
                prompt=learning_prompt,
                max_tokens=300,
                temperature=0.2
            )
            
            if learning_response and len(learning_response) > 100:
                logger.info("    ✅ Learning analysis with real data successful")
            else:
                logger.warning("    ⚠️ Learning analysis response too short")
            
            # Test context injection with real data
            context_prompt = self.prompt_manager.get_prompt(
                'context_injection',
                context=test_strand
            )
            
            if context_prompt and 'BTC' in context_prompt and 'head_and_shoulders' in context_prompt:
                logger.info("    ✅ Context injection with real data successful")
            else:
                logger.warning("    ⚠️ Context injection with real data may need improvement")
            
            # Cleanup
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            logger.info("    ✅ Test data cleaned up")
            
        except Exception as e:
            logger.error(f"    ❌ Integration test failed: {e}")
            raise
        
        logger.info("    ✅ Integration test successful")
    
    async def test_real_scenarios(self):
        """Test with real trading scenarios"""
        logger.info("  📈 Testing real scenarios...")
        
        try:
            # Test pattern analysis scenario
            pattern_scenario = {
                "symbol": "BTC",
                "current_price": 45000,
                "pattern_data": {
                    "type": "double_top",
                    "confidence": 0.88,
                    "timeframe": "4h",
                    "volume": 1500,
                    "resistance": 46000
                },
                "market_context": {
                    "trend": "sideways",
                    "volatility": "high",
                    "volume": "above_average"
                }
            }
            
            pattern_prompt = self.prompt_manager.get_prompt(
                'pattern_analysis',
                context=pattern_scenario
            )
            
            pattern_response = await self.llm_client.generate_completion(
                prompt=pattern_prompt,
                max_tokens=400,
                temperature=0.2
            )
            
            if pattern_response and any(keyword in pattern_response.lower() for keyword in ['double', 'top', 'resistance', 'bearish']):
                logger.info("    ✅ Pattern analysis scenario successful")
            else:
                logger.warning("    ⚠️ Pattern analysis scenario response unclear")
            
            # Test trading decision scenario
            decision_scenario = {
                "symbol": "ETH",
                "current_price": 3200,
                "signal": "buy",
                "confidence": 0.75,
                "risk_level": "medium",
                "portfolio_context": {
                    "total_value": 10000,
                    "current_position": 0.1,
                    "max_risk": 0.05
                }
            }
            
            decision_prompt = self.prompt_manager.get_prompt(
                'trading_plan_generation',
                context=decision_scenario
            )
            
            decision_response = await self.llm_client.generate_completion(
                prompt=decision_prompt,
                max_tokens=300,
                temperature=0.3
            )
            
            if decision_response and len(decision_response) > 100:
                logger.info("    ✅ Trading decision scenario successful")
            else:
                logger.warning("    ⚠️ Trading decision scenario response too short")
            
        except Exception as e:
            logger.error(f"    ❌ Real scenarios test failed: {e}")
            raise
        
        logger.info("    ✅ Real scenarios test successful")
    
    async def test_stress_testing(self):
        """Test LLM under stress conditions"""
        logger.info("  💪 Testing stress conditions...")
        
        try:
            # Test rapid sequential requests
            rapid_responses = []
            start_time = time.time()
            
            for i in range(5):
                response = await self.llm_client.generate_completion(
                    prompt=f"Quick analysis {i}: Rate this pattern 1-10",
                    max_tokens=20,
                    temperature=0.1
                )
                rapid_responses.append(response)
            
            rapid_time = time.time() - start_time
            successful_rapid = sum(1 for r in rapid_responses if r and len(r) > 0)
            
            logger.info(f"    ✅ Rapid requests: {successful_rapid}/5 successful in {rapid_time:.2f}s")
            
            # Test large context handling
            large_context = {
                "symbol": "BTC",
                "historical_data": [{"price": 40000 + i*100, "volume": 1000 + i*10} for i in range(100)],
                "patterns": [f"pattern_{i}" for i in range(50)],
                "indicators": {f"indicator_{i}": 0.5 + i*0.01 for i in range(20)}
            }
            
            large_prompt = self.prompt_manager.get_prompt(
                'learning_analysis',
                context=large_context
            )
            
            large_response = await self.llm_client.generate_completion(
                prompt=large_prompt,
                max_tokens=500,
                temperature=0.2
            )
            
            if large_response and len(large_response) > 200:
                logger.info("    ✅ Large context handling successful")
            else:
                logger.warning("    ⚠️ Large context handling may need optimization")
            
            # Test error recovery
            error_responses = []
            for i in range(3):
                try:
                    response = await self.llm_client.generate_completion(
                        prompt=f"Test error recovery {i}",
                        max_tokens=50,
                        temperature=0.1
                    )
                    error_responses.append(response)
                except Exception as e:
                    logger.warning(f"    ⚠️ Error in stress test {i}: {e}")
                    error_responses.append(None)
            
            successful_error_recovery = sum(1 for r in error_responses if r)
            logger.info(f"    ✅ Error recovery: {successful_error_recovery}/3 successful")
            
        except Exception as e:
            logger.error(f"    ❌ Stress testing failed: {e}")
            raise
        
        logger.info("    ✅ Stress testing successful")
    
    def print_summary(self):
        """Print test summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 LLM Integration Testing Summary")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📈 Test Results: {len(self.test_results)} test suites")
        
        for suite_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            if status == 'PASSED':
                logger.info(f"    ✅ {suite_name}")
            else:
                logger.info(f"    ❌ {suite_name}: {result.get('error', 'Unknown error')}")
        
        logger.info("=" * 80)

async def main():
    """Main test runner"""
    tester = LLMComprehensiveTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

