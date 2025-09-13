#!/usr/bin/env python3
"""
Real LLM Integration Test

This script tests the system with actual LLM API calls to validate
real-world performance and integration.
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealLLMIntegrationTest:
    """Test runner for real LLM integration"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.llm_client = None
        self.real_calls_made = 0
        self.real_responses = []
        
    async def run_real_llm_tests(self):
        """Run tests with real LLM calls"""
        logger.info("🚀 Starting Real LLM Integration Test")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        try:
            # Try to import real LLM client
            from llm_integration.openrouter_client import OpenRouterClient
            self.llm_client = OpenRouterClient()
            logger.info("✅ Real LLM client initialized")
        except ImportError as e:
            logger.error(f"❌ Failed to import real LLM client: {e}")
            logger.error("This test requires the actual LLM integration to be available")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM client: {e}")
            return False
        
        test_phases = [
            ("Basic LLM Call", self.test_basic_llm_call),
            ("Pattern Analysis", self.test_pattern_analysis),
            ("Prediction Generation", self.test_prediction_generation),
            ("Learning Insight", self.test_learning_insight),
            ("Braid Creation", self.test_braid_creation),
            ("Performance Test", self.test_performance),
            ("Error Handling", self.test_error_handling)
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
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 Real LLM Test Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"🤖 Real LLM Calls Made: {self.real_calls_made}")
        logger.info(f"📝 Real Responses Received: {len(self.real_responses)}")
        
        if failed == 0:
            logger.info("🎉 Real LLM integration test passed!")
            return True
        else:
            logger.error("⚠️  Some real LLM tests failed.")
            return False
    
    async def test_basic_llm_call(self):
        """Test basic LLM call"""
        logger.info("  🤖 Testing basic LLM call...")
        
        prompt = "Hello, can you respond with 'LLM integration test successful'?"
        
        try:
            response = await self.llm_client.generate_response(prompt)
            self.real_calls_made += 1
            
            assert response, "LLM call failed"
            assert 'content' in response, "Response missing content"
            assert isinstance(response['content'], str), "Content should be string"
            assert len(response['content']) > 0, "Content should not be empty"
            
            self.real_responses.append({
                'prompt': prompt,
                'response': response['content'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"    ✅ LLM Response: {response['content'][:100]}...")
            logger.info("  ✅ Basic LLM call successful")
            
        except Exception as e:
            logger.error(f"    ❌ Basic LLM call failed: {e}")
            raise
    
    async def test_pattern_analysis(self):
        """Test pattern analysis with real LLM"""
        logger.info("  🔍 Testing pattern analysis...")
        
        pattern_data = {
            'symbol': 'BTC',
            'price': 45000,
            'volume': 1500,
            'pattern_type': 'volume_spike',
            'confidence': 0.85,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        prompt = f"""
        Analyze this trading pattern and provide insights:
        
        Pattern Data: {json.dumps(pattern_data, indent=2)}
        
        Please provide:
        1. Pattern strength assessment
        2. Market implications
        3. Trading recommendations
        4. Risk factors
        """
        
        try:
            response = await self.llm_client.generate_response(prompt)
            self.real_calls_made += 1
            
            assert response, "Pattern analysis failed"
            assert 'content' in response, "Response missing content"
            assert len(response['content']) > 50, "Response too short for pattern analysis"
            
            self.real_responses.append({
                'prompt': prompt,
                'response': response['content'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"    ✅ Pattern Analysis: {response['content'][:150]}...")
            logger.info("  ✅ Pattern analysis successful")
            
        except Exception as e:
            logger.error(f"    ❌ Pattern analysis failed: {e}")
            raise
    
    async def test_prediction_generation(self):
        """Test prediction generation with real LLM"""
        logger.info("  🔮 Testing prediction generation...")
        
        market_context = {
            'current_price': 45000,
            'volume_trend': 'increasing',
            'market_sentiment': 'bullish',
            'technical_indicators': ['RSI: 65', 'MACD: bullish crossover', 'Volume: above average']
        }
        
        prompt = f"""
        Based on this market context, generate a trading prediction:
        
        Market Context: {json.dumps(market_context, indent=2)}
        
        Please provide:
        1. Price prediction for next 1 hour
        2. Confidence level (0-1)
        3. Key factors driving the prediction
        4. Risk assessment
        """
        
        try:
            response = await self.llm_client.generate_response(prompt)
            self.real_calls_made += 1
            
            assert response, "Prediction generation failed"
            assert 'content' in response, "Response missing content"
            assert len(response['content']) > 50, "Response too short for prediction"
            
            self.real_responses.append({
                'prompt': prompt,
                'response': response['content'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"    ✅ Prediction: {response['content'][:150]}...")
            logger.info("  ✅ Prediction generation successful")
            
        except Exception as e:
            logger.error(f"    ❌ Prediction generation failed: {e}")
            raise
    
    async def test_learning_insight(self):
        """Test learning insight generation with real LLM"""
        logger.info("  💡 Testing learning insight generation...")
        
        historical_data = {
            'successful_patterns': [
                {'pattern_type': 'volume_spike', 'success_rate': 0.85, 'avg_return': 0.03},
                {'pattern_type': 'price_breakout', 'success_rate': 0.78, 'avg_return': 0.025}
            ],
            'failed_patterns': [
                {'pattern_type': 'false_breakout', 'success_rate': 0.35, 'avg_return': -0.01}
            ],
            'market_conditions': ['high_volatility', 'trending_market']
        }
        
        prompt = f"""
        Analyze this historical trading data and generate learning insights:
        
        Historical Data: {json.dumps(historical_data, indent=2)}
        
        Please provide:
        1. Key patterns that work well
        2. Patterns to avoid
        3. Market conditions that favor success
        4. Recommendations for improving trading strategy
        """
        
        try:
            response = await self.llm_client.generate_response(prompt)
            self.real_calls_made += 1
            
            assert response, "Learning insight generation failed"
            assert 'content' in response, "Response missing content"
            assert len(response['content']) > 50, "Response too short for learning insight"
            
            self.real_responses.append({
                'prompt': prompt,
                'response': response['content'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"    ✅ Learning Insight: {response['content'][:150]}...")
            logger.info("  ✅ Learning insight generation successful")
            
        except Exception as e:
            logger.error(f"    ❌ Learning insight generation failed: {e}")
            raise
    
    async def test_braid_creation(self):
        """Test braid creation with real LLM"""
        logger.info("  🧬 Testing braid creation...")
        
        learning_insights = [
            "Volume spikes above 150% of average indicate strong buying pressure",
            "Price breakouts with volume confirmation have 85% success rate",
            "False breakouts often occur during low volatility periods"
        ]
        
        prompt = f"""
        Create a comprehensive trading braid from these learning insights:
        
        Learning Insights: {json.dumps(learning_insights, indent=2)}
        
        Please create a braid that:
        1. Synthesizes the key insights
        2. Provides actionable trading rules
        3. Includes risk management guidelines
        4. Specifies when to apply the braid
        """
        
        try:
            response = await self.llm_client.generate_response(prompt)
            self.real_calls_made += 1
            
            assert response, "Braid creation failed"
            assert 'content' in response, "Response missing content"
            assert len(response['content']) > 50, "Response too short for braid creation"
            
            self.real_responses.append({
                'prompt': prompt,
                'response': response['content'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            logger.info(f"    ✅ Braid Creation: {response['content'][:150]}...")
            logger.info("  ✅ Braid creation successful")
            
        except Exception as e:
            logger.error(f"    ❌ Braid creation failed: {e}")
            raise
    
    async def test_performance(self):
        """Test LLM performance with multiple calls"""
        logger.info("  ⚡ Testing LLM performance...")
        
        prompts = [
            "What is the current market sentiment?",
            "Analyze this price movement: +2.5% in 1 hour",
            "What are the key trading signals to watch?",
            "How do you assess market volatility?",
            "What is your trading recommendation?"
        ]
        
        start_time = time.time()
        responses = []
        
        try:
            for i, prompt in enumerate(prompts):
                response = await self.llm_client.generate_response(prompt)
                self.real_calls_made += 1
                responses.append(response)
                
                assert response, f"LLM call {i+1} failed"
                assert 'content' in response, f"Response {i+1} missing content"
                
                logger.info(f"    ✅ Call {i+1}/5 completed")
            
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / len(prompts)
            
            logger.info(f"    ✅ Performance: {len(prompts)} calls in {total_time:.2f}s")
            logger.info(f"    ✅ Average time per call: {avg_time:.2f}s")
            logger.info(f"    ✅ Calls per second: {len(prompts) / total_time:.2f}")
            
            # Performance assertions
            assert total_time < 60, "Performance too slow (over 60 seconds)"
            assert avg_time < 10, "Average call time too slow (over 10 seconds)"
            
            logger.info("  ✅ Performance test successful")
            
        except Exception as e:
            logger.error(f"    ❌ Performance test failed: {e}")
            raise
    
    async def test_error_handling(self):
        """Test LLM error handling"""
        logger.info("  ⚠️  Testing error handling...")
        
        # Test with very long prompt
        long_prompt = "A" * 10000  # Very long prompt
        
        try:
            response = await self.llm_client.generate_response(long_prompt)
            self.real_calls_made += 1
            
            # Should either work or handle gracefully
            if response and 'content' in response:
                logger.info("    ✅ Long prompt handled successfully")
            else:
                logger.info("    ✅ Long prompt rejected gracefully")
            
        except Exception as e:
            # Expected to handle long prompts
            logger.info(f"    ✅ Long prompt error handled: {type(e).__name__}")
        
        # Test with empty prompt
        try:
            response = await self.llm_client.generate_response("")
            self.real_calls_made += 1
            
            if response and 'content' in response:
                logger.info("    ✅ Empty prompt handled successfully")
            else:
                logger.info("    ✅ Empty prompt rejected gracefully")
                
        except Exception as e:
            # Expected to handle empty prompts
            logger.info(f"    ✅ Empty prompt error handled: {type(e).__name__}")
        
        logger.info("  ✅ Error handling test successful")

async def main():
    """Main test runner"""
    test_runner = RealLLMIntegrationTest()
    
    try:
        success = await test_runner.run_real_llm_tests()
        
        if success:
            logger.info("\n🎉 Real LLM integration test passed!")
            logger.info("The system is working with actual LLM API calls.")
            return 0
        else:
            logger.error("\n⚠️  Real LLM integration test failed.")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test suite crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

