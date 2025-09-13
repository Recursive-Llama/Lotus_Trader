#!/usr/bin/env python3
"""
Real LLM Validation Test
Tests actual LLM API calls with real prompts to ensure the system actually works
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class RealLLMValidator:
    def __init__(self):
        self.test_results = {}
        self.llm_responses = []
        
    async def test_llm_client_initialization(self):
        """Test if we can actually initialize the LLM client"""
        print("🔧 Testing LLM Client Initialization...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test 1: Check if we can import OpenRouterClient
            print("  Testing OpenRouterClient import...")
            try:
                from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
                results["passed"] += 1
                print("  ✅ OpenRouterClient imported successfully")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ OpenRouterClient import failed: {e}")
                return False
            
            # Test 2: Try to instantiate the client
            print("  Testing OpenRouterClient instantiation...")
            try:
                client = OpenRouterClient()
                results["passed"] += 1
                print("  ✅ OpenRouterClient instantiated successfully")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ OpenRouterClient instantiation failed: {e}")
                return False
            
            # Test 3: Check if we can import PromptManager
            print("  Testing PromptManager import...")
            try:
                from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
                results["passed"] += 1
                print("  ✅ PromptManager imported successfully")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ PromptManager import failed: {e}")
                return False
            
            # Test 4: Try to instantiate PromptManager
            print("  Testing PromptManager instantiation...")
            try:
                prompt_manager = PromptManager()
                results["passed"] += 1
                print("  ✅ PromptManager instantiated successfully")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ PromptManager instantiation failed: {e}")
                return False
            
            results["details"] = {
                "openrouter_import": True,
                "openrouter_instantiation": True,
                "prompt_manager_import": True,
                "prompt_manager_instantiation": True
            }
            
            self.test_results["llm_initialization"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ LLM initialization test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_real_llm_api_calls(self):
        """Test actual LLM API calls with real prompts"""
        print("\n🧠 Testing Real LLM API Calls...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Initialize components
            try:
                from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
                from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
                
                client = OpenRouterClient()
                prompt_manager = PromptManager()
                
                results["passed"] += 1
                print("  ✅ LLM components initialized")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ LLM component initialization failed: {e}")
                return False
            
            # Test 1: Simple LLM call
            print("  Testing simple LLM call...")
            try:
                start_time = time.time()
                response = await client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
                    max_tokens=10
                )
                response_time = time.time() - start_time
                
                if response and len(response.strip()) > 0:
                    results["passed"] += 1
                    print(f"  ✅ Simple LLM call successful: '{response.strip()}' ({response_time:.2f}s)")
                    self.llm_responses.append({
                        "type": "simple",
                        "response": response,
                        "response_time": response_time
                    })
                else:
                    results["failed"] += 1
                    print(f"  ❌ Simple LLM call returned empty response")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Simple LLM call failed: {e}")
            
            # Test 2: Pattern analysis prompt
            print("  Testing pattern analysis prompt...")
            try:
                # Create test strands
                test_strands = [
                    {
                        "strand_type": "pattern",
                        "content": "RSI divergence detected on 1H timeframe",
                        "metadata": {
                            "rsi": 30,
                            "timeframe": "1H",
                            "confidence": 0.8,
                            "pattern_type": "rsi_divergence"
                        }
                    },
                    {
                        "strand_type": "pattern",
                        "content": "Volume spike with price drop",
                        "metadata": {
                            "volume": 1500000,
                            "price_change": -0.05,
                            "confidence": 0.7,
                            "pattern_type": "volume_spike"
                        }
                    }
                ]
                
                # Get prompt template
                prompt_template = prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    "pattern_analysis"
                )
                
                # Format prompt
                formatted_prompt = prompt_template.format(strands=test_strands)
                
                # Make LLM call
                start_time = time.time()
                response = await client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=300
                )
                response_time = time.time() - start_time
                
                if response and len(response.strip()) > 50:
                    results["passed"] += 1
                    print(f"  ✅ Pattern analysis prompt successful ({response_time:.2f}s)")
                    print(f"    Response preview: {response[:100]}...")
                    self.llm_responses.append({
                        "type": "pattern_analysis",
                        "response": response,
                        "response_time": response_time
                    })
                else:
                    results["failed"] += 1
                    print(f"  ❌ Pattern analysis prompt returned insufficient response")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Pattern analysis prompt failed: {e}")
            
            # Test 3: Trade outcome braiding prompt
            print("  Testing trade outcome braiding prompt...")
            try:
                test_strands = [
                    {
                        "strand_type": "trade_outcome",
                        "content": "Trade executed: BUY 100 shares at $50, sold at $55",
                        "metadata": {
                            "action": "BUY",
                            "quantity": 100,
                            "entry_price": 50,
                            "exit_price": 55,
                            "profit": 500,
                            "outcome": "success"
                        }
                    }
                ]
                
                # Get prompt template
                prompt_template = prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    "trade_outcome_braiding"
                )
                
                # Format prompt
                formatted_prompt = prompt_template.format(strands=test_strands)
                
                # Make LLM call
                start_time = time.time()
                response = await client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=300
                )
                response_time = time.time() - start_time
                
                if response and len(response.strip()) > 50:
                    results["passed"] += 1
                    print(f"  ✅ Trade outcome braiding prompt successful ({response_time:.2f}s)")
                    print(f"    Response preview: {response[:100]}...")
                    self.llm_responses.append({
                        "type": "trade_outcome_braiding",
                        "response": response,
                        "response_time": response_time
                    })
                else:
                    results["failed"] += 1
                    print(f"  ❌ Trade outcome braiding prompt returned insufficient response")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Trade outcome braiding prompt failed: {e}")
            
            results["details"] = {
                "llm_responses": len(self.llm_responses),
                "response_times": [r["response_time"] for r in self.llm_responses]
            }
            
            self.test_results["real_llm_calls"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Real LLM API calls test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_llm_response_quality(self):
        """Test the quality of LLM responses"""
        print("\n📊 Testing LLM Response Quality...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            if not self.llm_responses:
                results["failed"] += 1
                print("  ❌ No LLM responses to validate")
                return False
            
            # Test response quality for each type
            for i, response_data in enumerate(self.llm_responses):
                response = response_data["response"]
                response_time = response_data["response_time"]
                response_type = response_data["type"]
                
                print(f"  Testing {response_type} response quality...")
                
                # Basic quality checks
                quality_score = 0
                issues = []
                
                # Length check
                if len(response.strip()) >= 10:
                    quality_score += 1
                else:
                    issues.append("Response too short")
                
                # Response time check
                if response_time < 10.0:
                    quality_score += 1
                else:
                    issues.append("Response too slow")
                
                # Content quality check
                if any(word in response.lower() for word in ["analysis", "pattern", "trade", "insight", "strategy"]):
                    quality_score += 1
                else:
                    issues.append("Response lacks relevant content")
                
                # Coherence check
                if len(response.split()) >= 5:  # At least 5 words
                    quality_score += 1
                else:
                    issues.append("Response lacks coherence")
                
                if quality_score >= 3:
                    results["passed"] += 1
                    print(f"    ✅ {response_type} quality: {quality_score}/4")
                else:
                    results["failed"] += 1
                    print(f"    ❌ {response_type} quality: {quality_score}/4 - {', '.join(issues)}")
            
            results["details"] = {
                "responses_tested": len(self.llm_responses),
                "quality_scores": [self._calculate_quality_score(r) for r in self.llm_responses]
            }
            
            self.test_results["llm_response_quality"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ LLM response quality test failed: {e}")
            traceback.print_exc()
            return False
    
    def _calculate_quality_score(self, response_data):
        """Calculate quality score for a response"""
        response = response_data["response"]
        response_time = response_data["response_time"]
        
        score = 0
        
        # Length check
        if len(response.strip()) >= 10:
            score += 1
        
        # Response time check
        if response_time < 10.0:
            score += 1
        
        # Content quality check
        if any(word in response.lower() for word in ["analysis", "pattern", "trade", "insight", "strategy"]):
            score += 1
        
        # Coherence check
        if len(response.split()) >= 5:
            score += 1
        
        return score
    
    async def test_end_to_end_llm_workflow(self):
        """Test complete end-to-end LLM workflow"""
        print("\n🔄 Testing End-to-End LLM Workflow...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test complete workflow: Market data -> Strands -> LLM -> Insights
            print("  Testing complete LLM workflow...")
            
            # Step 1: Create test market data
            market_data = {
                "symbol": "BTCUSDT",
                "timestamp": datetime.now().isoformat(),
                "open": 50000.0,
                "high": 51000.0,
                "low": 49500.0,
                "close": 50500.0,
                "volume": 1000000.0,
                "rsi": 65.5
            }
            
            # Step 2: Process into strands
            strands = self._process_market_data_to_strands(market_data)
            
            if len(strands) > 0:
                results["passed"] += 1
                print(f"  ✅ Created {len(strands)} strands from market data")
            else:
                results["failed"] += 1
                print("  ❌ Failed to create strands")
                return False
            
            # Step 3: Calculate resonance
            try:
                from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                engine = MathematicalResonanceEngine()
                
                pattern_data = {
                    "accuracy": 0.8,
                    "precision": 0.75,
                    "stability": 0.8
                }
                timeframes = ["1H", "4H", "1D"]
                phi = engine.calculate_phi(pattern_data, timeframes)
                
                if 0 <= phi <= 1:
                    results["passed"] += 1
                    print(f"  ✅ Resonance calculated: φ = {phi:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Invalid resonance: φ = {phi:.3f}")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Resonance calculation failed: {e}")
            
            # Step 4: Generate LLM insights
            try:
                from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
                from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
                
                client = OpenRouterClient()
                prompt_manager = PromptManager()
                
                # Get pattern analysis prompt
                prompt_template = prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    "pattern_analysis"
                )
                
                formatted_prompt = prompt_template.format(strands=strands)
                
                start_time = time.time()
                llm_response = await client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=300
                )
                response_time = time.time() - start_time
                
                if llm_response and len(llm_response.strip()) > 50:
                    results["passed"] += 1
                    print(f"  ✅ LLM insights generated ({response_time:.2f}s)")
                    print(f"    Insight preview: {llm_response[:100]}...")
                else:
                    results["failed"] += 1
                    print("  ❌ LLM insights generation failed")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ LLM insights generation failed: {e}")
            
            # Step 5: Validate complete workflow
            if results["passed"] >= 3:  # At least 3 out of 4 steps successful
                results["passed"] += 1
                print("  ✅ Complete LLM workflow successful")
            else:
                results["failed"] += 1
                print("  ❌ Complete LLM workflow failed")
            
            results["details"] = {
                "strands_created": len(strands),
                "resonance_calculated": phi if 'phi' in locals() else None,
                "llm_response_time": response_time if 'response_time' in locals() else None,
                "workflow_success": results["passed"] >= 4
            }
            
            self.test_results["end_to_end_llm_workflow"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ End-to-end LLM workflow test failed: {e}")
            traceback.print_exc()
            return False
    
    def _process_market_data_to_strands(self, market_data):
        """Process market data into strands"""
        strands = []
        
        # RSI pattern
        if "rsi" in market_data:
            rsi = market_data["rsi"]
            if rsi < 30:
                pattern_type = "rsi_oversold"
                confidence = 0.8
            elif rsi > 70:
                pattern_type = "rsi_overbought"
                confidence = 0.8
            else:
                pattern_type = "rsi_neutral"
                confidence = 0.5
            
            strands.append({
                "strand_type": "pattern",
                "content": f"RSI {pattern_type} signal at {rsi:.1f}",
                "metadata": {
                    "rsi": rsi,
                    "pattern_type": pattern_type,
                    "confidence": confidence,
                    "timeframe": "1H",
                    "accuracy": 0.8,
                    "precision": 0.75,
                    "stability": 0.8,
                    "price": market_data["close"]
                },
                "source": "rsi_analyzer",
                "created_at": market_data["timestamp"]
            })
        
        return strands
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 REAL LLM VALIDATION TEST SUMMARY")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        
        for test_name, results in self.test_results.items():
            if isinstance(results, dict) and "passed" in results and "failed" in results:
                passed = results["passed"]
                failed = results["failed"]
                total_passed += passed
                total_failed += failed
                
                status = "✅ PASS" if failed == 0 else "❌ FAIL"
                print(f"{test_name.upper().replace('_', ' ')}: {status} ({passed} passed, {failed} failed)")
        
        print("-"*80)
        overall_status = "✅ ALL LLM TESTS PASSED" if total_failed == 0 else "❌ SOME LLM TESTS FAILED"
        print(f"OVERALL: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*80)
        
        if total_failed == 0:
            print("\n🎉 LLM integration is working correctly!")
            print("✅ Real API calls are successful")
            print("✅ Response quality is good")
            print("✅ End-to-end workflow is functional")
        else:
            print("\n⚠️  LLM integration has issues that need fixing")
            print("❌ System may not work in production")
        
        return total_failed == 0

async def main():
    """Run real LLM validation tests"""
    print("🚀 Starting Real LLM Validation Tests")
    print("="*80)
    
    validator = RealLLMValidator()
    
    # Run all tests
    tests = [
        ("LLM Client Initialization", validator.test_llm_client_initialization),
        ("Real LLM API Calls", validator.test_real_llm_api_calls),
        ("LLM Response Quality", validator.test_llm_response_quality),
        ("End-to-End LLM Workflow", validator.test_end_to_end_llm_workflow)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name}...")
            await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            traceback.print_exc()
    
    # Print summary
    success = validator.print_summary()
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
