#!/usr/bin/env python3
"""
LLM Response Quality Validation Test
Tests that LLM calls produce high-quality, relevant responses
"""

import sys
import os
import asyncio
import json
import time
from typing import Dict, List, Any
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager

class LLMQualityTester:
    def __init__(self):
        self.llm_client = OpenRouterClient()
        self.prompt_manager = PromptManager()
        self.test_results = []
    
    async def test_pattern_analysis_quality(self):
        """Test pattern analysis LLM responses for quality"""
        print("🔍 Testing Pattern Analysis Quality...")
        
        test_cases = [
            {
                "name": "RSI Divergence Analysis",
                "strands": [
                    {
                        "type": "pattern",
                        "content": "RSI divergence detected on 1H timeframe",
                        "metadata": {
                            "rsi": 30,
                            "price": 50000,
                            "timeframe": "1H",
                            "confidence": 0.8
                        }
                    },
                    {
                        "type": "pattern", 
                        "content": "Volume spike with price drop",
                        "metadata": {
                            "volume": 1500000,
                            "price_change": -0.05,
                            "confidence": 0.7
                        }
                    }
                ],
                "expected_keywords": ["divergence", "rsi", "volume", "analysis", "pattern", "signal"],
                "min_length": 100,
                "max_length": 1000
            },
            {
                "name": "Moving Average Cross",
                "strands": [
                    {
                        "type": "pattern",
                        "content": "Golden cross detected: 50MA crossed above 200MA",
                        "metadata": {
                            "ma_50": 50500,
                            "ma_200": 50000,
                            "crossover_type": "golden",
                            "confidence": 0.9
                        }
                    }
                ],
                "expected_keywords": ["golden", "cross", "moving", "average", "bullish", "trend"],
                "min_length": 80,
                "max_length": 800
            }
        ]
        
        for test_case in test_cases:
            try:
                # Get prompt template
                prompt_template = self.prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    "pattern_analysis"
                )
                
                # Format prompt
                formatted_prompt = prompt_template.format(
                    strands=test_case["strands"]
                )
                
                # Make LLM call
                start_time = time.time()
                response = await self.llm_client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=500
                )
                response_time = time.time() - start_time
                
                # Validate response
                validation = self._validate_response_quality(
                    response,
                    test_case["expected_keywords"],
                    test_case["min_length"],
                    test_case["max_length"],
                    response_time
                )
                
                result = {
                    "test_name": test_case["name"],
                    "passed": validation["passed"],
                    "quality_score": validation["quality_score"],
                    "response_time": response_time,
                    "response_length": len(response) if response else 0,
                    "details": validation
                }
                
                self.test_results.append(result)
                
                status = "✅ PASS" if validation["passed"] else "❌ FAIL"
                print(f"  {status} {test_case['name']} - Quality: {validation['quality_score']}/10")
                
            except Exception as e:
                print(f"  ❌ ERROR {test_case['name']}: {e}")
                self.test_results.append({
                    "test_name": test_case["name"],
                    "passed": False,
                    "error": str(e)
                })
    
    async def test_trade_outcome_braiding_quality(self):
        """Test trade outcome braiding LLM responses for quality"""
        print("\n💰 Testing Trade Outcome Braiding Quality...")
        
        test_cases = [
            {
                "name": "Successful Trade Analysis",
                "strands": [
                    {
                        "type": "trade_outcome",
                        "content": "Trade executed: BUY 100 shares at $50, sold at $55",
                        "metadata": {
                            "action": "BUY",
                            "quantity": 100,
                            "entry_price": 50,
                            "exit_price": 55,
                            "profit": 500,
                            "outcome": "success"
                        }
                    },
                    {
                        "type": "trade_outcome",
                        "content": "Stop loss triggered at $48",
                        "metadata": {
                            "action": "SELL",
                            "quantity": 50,
                            "entry_price": 50,
                            "exit_price": 48,
                            "loss": -100,
                            "outcome": "loss"
                        }
                    }
                ],
                "expected_keywords": ["trade", "profit", "loss", "strategy", "lesson", "outcome"],
                "min_length": 120,
                "max_length": 1000
            },
            {
                "name": "Risk Management Analysis",
                "strands": [
                    {
                        "type": "trade_outcome",
                        "content": "Position size too large, caused significant drawdown",
                        "metadata": {
                            "position_size": 0.1,
                            "drawdown": -0.15,
                            "outcome": "poor_risk_management"
                        }
                    }
                ],
                "expected_keywords": ["risk", "position", "size", "drawdown", "management", "lesson"],
                "min_length": 100,
                "max_length": 800
            }
        ]
        
        for test_case in test_cases:
            try:
                # Get prompt template
                prompt_template = self.prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    "trade_outcome_braiding"
                )
                
                # Format prompt
                formatted_prompt = prompt_template.format(
                    strands=test_case["strands"]
                )
                
                # Make LLM call
                start_time = time.time()
                response = await self.llm_client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=500
                )
                response_time = time.time() - start_time
                
                # Validate response
                validation = self._validate_response_quality(
                    response,
                    test_case["expected_keywords"],
                    test_case["min_length"],
                    test_case["max_length"],
                    response_time
                )
                
                result = {
                    "test_name": test_case["name"],
                    "passed": validation["passed"],
                    "quality_score": validation["quality_score"],
                    "response_time": response_time,
                    "response_length": len(response) if response else 0,
                    "details": validation
                }
                
                self.test_results.append(result)
                
                status = "✅ PASS" if validation["passed"] else "❌ FAIL"
                print(f"  {status} {test_case['name']} - Quality: {validation['quality_score']}/10")
                
            except Exception as e:
                print(f"  ❌ ERROR {test_case['name']}: {e}")
                self.test_results.append({
                    "test_name": test_case["name"],
                    "passed": False,
                    "error": str(e)
                })
    
    async def test_prediction_review_quality(self):
        """Test prediction review LLM responses for quality"""
        print("\n🎯 Testing Prediction Review Quality...")
        
        test_cases = [
            {
                "name": "Price Prediction Accuracy",
                "strands": [
                    {
                        "type": "prediction_review",
                        "content": "Predicted BTC to reach $52k - actual: $50.5k",
                        "metadata": {
                            "predicted_price": 52000,
                            "actual_price": 50500,
                            "accuracy": 0.75,
                            "confidence": 0.8
                        }
                    },
                    {
                        "type": "prediction_review",
                        "content": "Volatility prediction: 15% - actual: 12%",
                        "metadata": {
                            "predicted_volatility": 0.15,
                            "actual_volatility": 0.12,
                            "accuracy": 0.8,
                            "confidence": 0.7
                        }
                    }
                ],
                "expected_keywords": ["prediction", "accuracy", "actual", "review", "lesson", "improvement"],
                "min_length": 100,
                "max_length": 1000
            }
        ]
        
        for test_case in test_cases:
            try:
                # Get prompt template
                prompt_template = self.prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    "prediction_review_braiding"
                )
                
                # Format prompt
                formatted_prompt = prompt_template.format(
                    strands=test_case["strands"]
                )
                
                # Make LLM call
                start_time = time.time()
                response = await self.llm_client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=500
                )
                response_time = time.time() - start_time
                
                # Validate response
                validation = self._validate_response_quality(
                    response,
                    test_case["expected_keywords"],
                    test_case["min_length"],
                    test_case["max_length"],
                    response_time
                )
                
                result = {
                    "test_name": test_case["name"],
                    "passed": validation["passed"],
                    "quality_score": validation["quality_score"],
                    "response_time": response_time,
                    "response_length": len(response) if response else 0,
                    "details": validation
                }
                
                self.test_results.append(result)
                
                status = "✅ PASS" if validation["passed"] else "❌ FAIL"
                print(f"  {status} {test_case['name']} - Quality: {validation['quality_score']}/10")
                
            except Exception as e:
                print(f"  ❌ ERROR {test_case['name']}: {e}")
                self.test_results.append({
                    "test_name": test_case["name"],
                    "passed": False,
                    "error": str(e)
                })
    
    def _validate_response_quality(self, response: str, expected_keywords: List[str], 
                                 min_length: int, max_length: int, response_time: float) -> Dict:
        """Validate LLM response quality"""
        if not response:
            return {
                "passed": False,
                "quality_score": 0,
                "reason": "Empty response"
            }
        
        quality_score = 0
        issues = []
        
        # Length validation
        response_length = len(response.strip())
        if min_length <= response_length <= max_length:
            quality_score += 2
        elif response_length < min_length:
            quality_score += 1
            issues.append(f"Too short: {response_length} < {min_length}")
        else:
            quality_score += 1
            issues.append(f"Too long: {response_length} > {max_length}")
        
        # Keyword presence
        found_keywords = []
        for keyword in expected_keywords:
            if keyword.lower() in response.lower():
                found_keywords.append(keyword)
        
        keyword_coverage = len(found_keywords) / len(expected_keywords)
        quality_score += int(keyword_coverage * 3)
        
        if keyword_coverage < 0.5:
            issues.append(f"Low keyword coverage: {keyword_coverage:.2f}")
        
        # Response time validation
        if response_time < 3.0:
            quality_score += 2
        elif response_time < 5.0:
            quality_score += 1
        else:
            issues.append(f"Slow response: {response_time:.2f}s")
        
        # Coherence checks
        coherence_score = 0
        
        # Check for structured analysis
        if any(word in response.lower() for word in ["analysis", "insight", "pattern", "strategy"]):
            coherence_score += 1
        
        # Check for actionable content
        if any(word in response.lower() for word in ["lesson", "improvement", "recommendation", "suggestion"]):
            coherence_score += 1
        
        # Check for specific details
        if any(char.isdigit() for char in response):
            coherence_score += 1
        
        quality_score += coherence_score
        
        if coherence_score < 2:
            issues.append("Low coherence/actionability")
        
        # Determine if passed
        passed = quality_score >= 7 and keyword_coverage >= 0.4 and response_time < 10.0
        
        return {
            "passed": passed,
            "quality_score": quality_score,
            "keyword_coverage": keyword_coverage,
            "found_keywords": found_keywords,
            "response_length": response_length,
            "response_time": response_time,
            "coherence_score": coherence_score,
            "issues": issues,
            "reason": "; ".join(issues) if issues else "Good quality"
        }
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 LLM RESPONSE QUALITY TEST SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("passed", False))
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "✅" if result.get("passed", False) else "❌"
            quality = result.get("quality_score", 0)
            time_taken = result.get("response_time", 0)
            print(f"  {status} {result['test_name']} - Quality: {quality}/10, Time: {time_taken:.2f}s")
        
        print("="*60)
        
        return failed_tests == 0

async def main():
    """Run LLM quality tests"""
    print("🧠 Starting LLM Response Quality Tests")
    print("="*60)
    
    tester = LLMQualityTester()
    
    # Run all quality tests
    await tester.test_pattern_analysis_quality()
    await tester.test_trade_outcome_braiding_quality()
    await tester.test_prediction_review_quality()
    
    # Print summary
    success = tester.print_summary()
    
    if success:
        print("\n🎉 All LLM quality tests passed!")
    else:
        print("\n⚠️  Some LLM quality tests failed. Review responses for improvement.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
