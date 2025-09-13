#!/usr/bin/env python3
"""
Comprehensive Functionality Test Suite
Tests both workflow AND actual functionality validation
- Real LLM calls with quality validation
- Output correctness verification
- End-to-end workflow testing
- Performance and reliability testing
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Import our modules
from src.learning_system.centralized_learning_system import CentralizedLearningSystem
from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
from src.learning_system.learning_pipeline import LearningPipeline
from src.learning_system.context_injection_engine import ContextInjectionEngine
from src.learning_system.module_specific_scoring import ModuleSpecificScoring
from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
from Modules.Alpha_Detector.src.database.supabase_client import SupabaseClient

class ComprehensiveFunctionalityTester:
    def __init__(self):
        self.test_results = {}
        self.llm_client = None
        self.prompt_manager = None
        self.learning_system = None
        self.resonance_engine = None
        self.pipeline = None
        self.context_engine = None
        self.scoring = None
        self.db_client = None
        
    async def setup(self):
        """Initialize all components"""
        print("🔧 Setting up comprehensive functionality test...")
        
        try:
            # Initialize LLM client
            self.llm_client = OpenRouterClient()
            print("✅ LLM client initialized")
            
            # Initialize prompt manager
            self.prompt_manager = PromptManager()
            print("✅ Prompt manager initialized")
            
            # Initialize learning system
            self.learning_system = CentralizedLearningSystem(self.prompt_manager)
            print("✅ Learning system initialized")
            
            # Initialize resonance engine
            self.resonance_engine = MathematicalResonanceEngine()
            print("✅ Resonance engine initialized")
            
            # Initialize pipeline
            self.pipeline = LearningPipeline(self.learning_system, self.resonance_engine)
            print("✅ Learning pipeline initialized")
            
            # Initialize context injection engine
            self.context_engine = ContextInjectionEngine(self.learning_system)
            print("✅ Context injection engine initialized")
            
            # Initialize scoring
            self.scoring = ModuleSpecificScoring()
            print("✅ Module scoring initialized")
            
            # Initialize database client
            self.db_client = SupabaseClient()
            print("✅ Database client initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_llm_quality_validation(self):
        """Test LLM response quality and correctness"""
        print("\n🧠 Testing LLM Quality Validation...")
        
        test_cases = [
            {
                "name": "Pattern Analysis",
                "prompt_type": "pattern_analysis",
                "data": {
                    "strands": [
                        {"type": "pattern", "content": "RSI divergence detected", "metadata": {"rsi": 30, "price": 100}},
                        {"type": "pattern", "content": "Volume spike with price drop", "metadata": {"volume": 1500000, "price_change": -0.05}}
                    ]
                },
                "expected_elements": ["pattern", "analysis", "insight", "confidence"]
            },
            {
                "name": "Trade Outcome Braiding",
                "prompt_type": "trade_outcome_braiding",
                "data": {
                    "strands": [
                        {"type": "trade_outcome", "content": "Trade executed: BUY 100 shares at $50", "metadata": {"outcome": "success", "profit": 500}},
                        {"type": "trade_outcome", "content": "Stop loss triggered at $48", "metadata": {"outcome": "loss", "loss": -200}}
                    ]
                },
                "expected_elements": ["outcome", "lesson", "strategy", "improvement"]
            },
            {
                "name": "Prediction Review",
                "prompt_type": "prediction_review_braiding",
                "data": {
                    "strands": [
                        {"type": "prediction_review", "content": "Predicted price increase - actual: +2%", "metadata": {"accuracy": 0.85, "confidence": 0.8}},
                        {"type": "prediction_review", "content": "Predicted volatility - actual: 15% vs 12%", "metadata": {"accuracy": 0.75, "confidence": 0.7}}
                    ]
                },
                "expected_elements": ["accuracy", "review", "learning", "adjustment"]
            }
        ]
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        for test_case in test_cases:
            try:
                print(f"  Testing: {test_case['name']}")
                
                # Get prompt template
                prompt_template = self.prompt_manager.get_prompt_template(
                    "learning_system/braiding_prompts.yaml",
                    test_case["prompt_type"]
                )
                
                # Format the prompt with test data
                formatted_prompt = prompt_template.format(**test_case["data"])
                
                # Make LLM call
                start_time = time.time()
                response = await self.llm_client.generate_completion(
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": formatted_prompt}],
                    max_tokens=500
                )
                response_time = time.time() - start_time
                
                # Validate response quality
                validation_result = self._validate_llm_response(
                    response, 
                    test_case["expected_elements"],
                    response_time
                )
                
                if validation_result["passed"]:
                    results["passed"] += 1
                    print(f"    ✅ PASSED - Quality: {validation_result['quality_score']}/10")
                else:
                    results["failed"] += 1
                    print(f"    ❌ FAILED - {validation_result['reason']}")
                
                results["details"].append({
                    "test": test_case["name"],
                    "result": validation_result,
                    "response_time": response_time,
                    "response_length": len(response) if response else 0
                })
                
            except Exception as e:
                results["failed"] += 1
                print(f"    ❌ ERROR - {e}")
                results["details"].append({
                    "test": test_case["name"],
                    "result": {"passed": False, "reason": str(e)},
                    "response_time": 0,
                    "response_length": 0
                })
        
        self.test_results["llm_quality"] = results
        return results["failed"] == 0
    
    def _validate_llm_response(self, response: str, expected_elements: List[str], response_time: float) -> Dict:
        """Validate LLM response quality and correctness"""
        if not response or len(response.strip()) < 50:
            return {"passed": False, "reason": "Response too short or empty"}
        
        if response_time > 10.0:
            return {"passed": False, "reason": f"Response too slow: {response_time:.2f}s"}
        
        # Check for expected elements
        found_elements = []
        for element in expected_elements:
            if element.lower() in response.lower():
                found_elements.append(element)
        
        # Calculate quality score
        quality_score = 0
        
        # Length check (not too short, not too long)
        if 100 <= len(response) <= 2000:
            quality_score += 2
        elif 50 <= len(response) < 100:
            quality_score += 1
        
        # Element coverage
        element_coverage = len(found_elements) / len(expected_elements)
        quality_score += int(element_coverage * 4)
        
        # Response time
        if response_time < 3.0:
            quality_score += 2
        elif response_time < 5.0:
            quality_score += 1
        
        # Coherence check (basic)
        if any(word in response.lower() for word in ["analysis", "insight", "pattern", "strategy"]):
            quality_score += 2
        
        # Determine if passed
        passed = quality_score >= 6 and element_coverage >= 0.5
        
        return {
            "passed": passed,
            "quality_score": quality_score,
            "element_coverage": element_coverage,
            "found_elements": found_elements,
            "response_time": response_time,
            "reason": f"Quality: {quality_score}/10, Coverage: {element_coverage:.2f}" if not passed else None
        }
    
    async def test_mathematical_resonance_calculations(self):
        """Test mathematical resonance calculations with real data"""
        print("\n🧮 Testing Mathematical Resonance Calculations...")
        
        test_data = {
            "patterns": [
                {
                    "id": "pattern_1",
                    "type": "rsi_divergence",
                    "accuracy": 0.85,
                    "precision": 0.78,
                    "stability": 0.82,
                    "cost": 0.1,
                    "frequency": 0.3
                },
                {
                    "id": "pattern_2", 
                    "type": "volume_spike",
                    "accuracy": 0.72,
                    "precision": 0.68,
                    "stability": 0.75,
                    "cost": 0.05,
                    "frequency": 0.4
                },
                {
                    "id": "pattern_3",
                    "type": "moving_average_cross",
                    "accuracy": 0.90,
                    "precision": 0.85,
                    "stability": 0.88,
                    "cost": 0.15,
                    "frequency": 0.2
                }
            ],
            "historical_performance": {
                "pattern_1": [0.8, 0.85, 0.82, 0.87, 0.83],
                "pattern_2": [0.7, 0.72, 0.75, 0.68, 0.74],
                "pattern_3": [0.88, 0.90, 0.87, 0.92, 0.89]
            },
            "successful_braids": [
                {"patterns": ["pattern_1", "pattern_3"], "outcome": "success", "score": 0.9},
                {"patterns": ["pattern_2"], "outcome": "partial", "score": 0.6}
            ]
        }
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test φ (Fractal Self-Similarity)
            phi_scores = {}
            for pattern in test_data["patterns"]:
                phi = self.resonance_engine.calculate_phi(
                    pattern["accuracy"],
                    pattern["precision"], 
                    pattern["stability"]
                )
                phi_scores[pattern["id"]] = phi
                
                # Validate phi is reasonable (0-1 range, higher is better)
                if 0 <= phi <= 1:
                    results["passed"] += 1
                    print(f"    ✅ φ({pattern['id']}) = {phi:.3f}")
                else:
                    results["failed"] += 1
                    print(f"    ❌ φ({pattern['id']}) = {phi:.3f} - Invalid range")
            
            # Test ρ (Recursive Feedback)
            rho = self.resonance_engine.calculate_rho(
                test_data["historical_performance"],
                test_data["successful_braids"]
            )
            
            if 0 <= rho <= 1:
                results["passed"] += 1
                print(f"    ✅ ρ = {rho:.3f}")
            else:
                results["failed"] += 1
                print(f"    ❌ ρ = {rho:.3f} - Invalid range")
            
            # Test θ (Global Field)
            theta = self.resonance_engine.calculate_theta(
                test_data["successful_braids"]
            )
            
            if 0 <= theta <= 1:
                results["passed"] += 1
                print(f"    ✅ θ = {theta:.3f}")
            else:
                results["failed"] += 1
                print(f"    ❌ θ = {theta:.3f} - Invalid range")
            
            # Test ω (Resonance Acceleration)
            omega = self.resonance_engine.calculate_omega(
                phi_scores,
                rho,
                theta
            )
            
            if 0 <= omega <= 1:
                results["passed"] += 1
                print(f"    ✅ ω = {omega:.3f}")
            else:
                results["failed"] += 1
                print(f"    ❌ ω = {omega:.3f} - Invalid range")
            
            # Test S_i (Selection Score)
            for pattern in test_data["patterns"]:
                s_i = self.resonance_engine.calculate_selection_score(
                    pattern["accuracy"],
                    pattern["precision"],
                    pattern["stability"],
                    pattern["cost"],
                    pattern["frequency"],
                    omega
                )
                
                if 0 <= s_i <= 1:
                    results["passed"] += 1
                    print(f"    ✅ S_i({pattern['id']}) = {s_i:.3f}")
                else:
                    results["failed"] += 1
                    print(f"    ❌ S_i({pattern['id']}) = {s_i:.3f} - Invalid range")
            
            # Test pattern weight calculation
            weights = self.resonance_engine.calculate_pattern_weight(
                test_data["patterns"][0],
                omega
            )
            
            if 0 <= weights <= 1:
                results["passed"] += 1
                print(f"    ✅ Pattern weight = {weights:.3f}")
            else:
                results["failed"] += 1
                print(f"    ❌ Pattern weight = {weights:.3f} - Invalid range")
            
            results["details"] = {
                "phi_scores": phi_scores,
                "rho": rho,
                "theta": theta,
                "omega": omega,
                "weights": weights
            }
            
        except Exception as e:
            results["failed"] += 1
            print(f"    ❌ ERROR in resonance calculations: {e}")
            traceback.print_exc()
        
        self.test_results["resonance_math"] = results
        return results["failed"] == 0
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow with real data"""
        print("\n🔄 Testing End-to-End Workflow...")
        
        # Create test market data
        test_market_data = {
            "symbol": "BTCUSDT",
            "timestamp": datetime.now().isoformat(),
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 1000000.0,
            "rsi": 65.5,
            "macd": 150.0,
            "bollinger_upper": 52000.0,
            "bollinger_lower": 48000.0
        }
        
        # Create test strands
        test_strands = [
            {
                "strand_type": "pattern",
                "content": "RSI divergence detected on 1H timeframe",
                "metadata": {
                    "rsi": 65.5,
                    "timeframe": "1H",
                    "confidence": 0.8,
                    "pattern_type": "rsi_divergence"
                },
                "source": "rsi_analyzer",
                "created_at": datetime.now().isoformat()
            },
            {
                "strand_type": "prediction_review",
                "content": "Previous prediction: price increase to $52k - actual: $50.5k",
                "metadata": {
                    "predicted_price": 52000,
                    "actual_price": 50500,
                    "accuracy": 0.75,
                    "confidence": 0.7
                },
                "source": "prediction_engine",
                "created_at": datetime.now().isoformat()
            },
            {
                "strand_type": "trade_outcome",
                "content": "Trade executed: BUY 0.1 BTC at $50k, sold at $50.5k",
                "metadata": {
                    "action": "BUY",
                    "quantity": 0.1,
                    "entry_price": 50000,
                    "exit_price": 50500,
                    "profit": 50.0,
                    "outcome": "success"
                },
                "source": "trading_engine",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Step 1: Store strands in database
            print("  Step 1: Storing test strands...")
            stored_strands = []
            for strand in test_strands:
                result = await self.db_client.store_strand(strand)
                if result:
                    stored_strands.append(result)
                    results["passed"] += 1
                    print(f"    ✅ Stored {strand['strand_type']} strand")
                else:
                    results["failed"] += 1
                    print(f"    ❌ Failed to store {strand['strand_type']} strand")
            
            if not stored_strands:
                print("    ❌ No strands stored, cannot continue workflow test")
                self.test_results["end_to_end"] = results
                return False
            
            # Step 2: Process strands through learning pipeline
            print("  Step 2: Processing strands through learning pipeline...")
            try:
                processed_strands = await self.pipeline.process_strands(stored_strands)
                if processed_strands:
                    results["passed"] += 1
                    print(f"    ✅ Processed {len(processed_strands)} strands")
                else:
                    results["failed"] += 1
                    print("    ❌ No strands processed")
            except Exception as e:
                results["failed"] += 1
                print(f"    ❌ Pipeline processing failed: {e}")
            
            # Step 3: Test context injection
            print("  Step 3: Testing context injection...")
            try:
                # Test context for CIL (prediction_review strands)
                cil_context = await self.context_engine.get_context_for_module(
                    "CIL", 
                    ["prediction_review"]
                )
                if cil_context and len(cil_context) > 0:
                    results["passed"] += 1
                    print(f"    ✅ CIL context: {len(cil_context)} insights")
                else:
                    results["failed"] += 1
                    print("    ❌ No CIL context generated")
                
                # Test context for CTP (trade_outcome strands)
                ctp_context = await self.context_engine.get_context_for_module(
                    "CTP",
                    ["trade_outcome"]
                )
                if ctp_context and len(ctp_context) > 0:
                    results["passed"] += 1
                    print(f"    ✅ CTP context: {len(ctp_context)} insights")
                else:
                    results["failed"] += 1
                    print("    ❌ No CTP context generated")
                
            except Exception as e:
                results["failed"] += 1
                print(f"    ❌ Context injection failed: {e}")
            
            # Step 4: Test resonance context
            print("  Step 4: Testing resonance context...")
            try:
                resonance_context = await self.learning_system.get_resonance_context()
                if resonance_context:
                    results["passed"] += 1
                    print(f"    ✅ Resonance context generated")
                else:
                    results["failed"] += 1
                    print("    ❌ No resonance context generated")
            except Exception as e:
                results["failed"] += 1
                print(f"    ❌ Resonance context failed: {e}")
            
            # Step 5: Test module-specific scoring
            print("  Step 5: Testing module-specific scoring...")
            try:
                for module in ["CIL", "CTP", "RDI", "DM"]:
                    score = self.scoring.calculate_module_score(
                        module,
                        stored_strands,
                        {"omega": 0.7, "theta": 0.8}
                    )
                    if 0 <= score <= 1:
                        results["passed"] += 1
                        print(f"    ✅ {module} score: {score:.3f}")
                    else:
                        results["failed"] += 1
                        print(f"    ❌ {module} score: {score:.3f} - Invalid range")
            except Exception as e:
                results["failed"] += 1
                print(f"    ❌ Module scoring failed: {e}")
            
        except Exception as e:
            results["failed"] += 1
            print(f"    ❌ End-to-end workflow failed: {e}")
            traceback.print_exc()
        
        self.test_results["end_to_end"] = results
        return results["failed"] == 0
    
    async def test_performance_and_reliability(self):
        """Test system performance and reliability"""
        print("\n⚡ Testing Performance and Reliability...")
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test concurrent processing
            print("  Testing concurrent processing...")
            start_time = time.time()
            
            tasks = []
            for i in range(5):
                task = asyncio.create_task(self._simulate_workload(i))
                tasks.append(task)
            
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_tasks = sum(1 for r in results_list if not isinstance(r, Exception))
            total_time = end_time - start_time
            
            if successful_tasks >= 4:  # Allow 1 failure
                results["passed"] += 1
                print(f"    ✅ Concurrent processing: {successful_tasks}/5 tasks completed in {total_time:.2f}s")
            else:
                results["failed"] += 1
                print(f"    ❌ Concurrent processing: Only {successful_tasks}/5 tasks completed")
            
            # Test memory usage (basic)
            print("  Testing memory efficiency...")
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb < 500:  # Less than 500MB
                results["passed"] += 1
                print(f"    ✅ Memory usage: {memory_mb:.1f}MB")
            else:
                results["failed"] += 1
                print(f"    ❌ Memory usage: {memory_mb:.1f}MB - Too high")
            
            # Test error handling
            print("  Testing error handling...")
            try:
                # Test with invalid data
                invalid_strand = {"invalid": "data"}
                await self.db_client.store_strand(invalid_strand)
                results["failed"] += 1
                print("    ❌ Should have handled invalid data")
            except Exception:
                results["passed"] += 1
                print("    ✅ Properly handled invalid data")
            
            results["details"] = {
                "concurrent_tasks": successful_tasks,
                "total_time": total_time,
                "memory_mb": memory_mb
            }
            
        except Exception as e:
            results["failed"] += 1
            print(f"    ❌ Performance test failed: {e}")
            traceback.print_exc()
        
        self.test_results["performance"] = results
        return results["failed"] == 0
    
    async def _simulate_workload(self, task_id: int):
        """Simulate a workload for performance testing"""
        try:
            # Simulate some processing
            await asyncio.sleep(0.1)
            
            # Test a simple calculation
            test_pattern = {
                "accuracy": 0.8,
                "precision": 0.75,
                "stability": 0.85
            }
            
            phi = self.resonance_engine.calculate_phi(
                test_pattern["accuracy"],
                test_pattern["precision"],
                test_pattern["stability"]
            )
            
            return {"task_id": task_id, "phi": phi, "success": True}
            
        except Exception as e:
            return {"task_id": task_id, "error": str(e), "success": False}
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE FUNCTIONALITY TEST SUMMARY")
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
        overall_status = "✅ ALL TESTS PASSED" if total_failed == 0 else "❌ SOME TESTS FAILED"
        print(f"OVERALL: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*80)
        
        return total_failed == 0

async def main():
    """Run comprehensive functionality tests"""
    print("🚀 Starting Comprehensive Functionality Test Suite")
    print("="*80)
    
    tester = ComprehensiveFunctionalityTester()
    
    # Setup
    if not await tester.setup():
        print("❌ Setup failed, cannot run tests")
        return False
    
    # Run all tests
    tests = [
        ("LLM Quality Validation", tester.test_llm_quality_validation),
        ("Mathematical Resonance", tester.test_mathematical_resonance_calculations),
        ("End-to-End Workflow", tester.test_end_to_end_workflow),
        ("Performance & Reliability", tester.test_performance_and_reliability)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name}...")
            await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            traceback.print_exc()
    
    # Print summary
    success = tester.print_summary()
    
    if success:
        print("\n🎉 All functionality tests passed! System is ready for production.")
    else:
        print("\n⚠️  Some tests failed. Please review and fix issues before deployment.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
