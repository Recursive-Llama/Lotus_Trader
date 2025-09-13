#!/usr/bin/env python3
"""
Simple Functionality Test
Tests core functionality without complex dependencies
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class SimpleFunctionalityTester:
    def __init__(self):
        self.test_results = {}
    
    async def test_mathematical_resonance_calculations(self):
        """Test mathematical resonance calculations"""
        print("🧮 Testing Mathematical Resonance Calculations...")
        
        try:
            from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
            
            engine = MathematicalResonanceEngine()
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test φ (Fractal Self-Similarity)
            pattern_data = {
                "accuracy": 0.85,
                "precision": 0.78,
                "stability": 0.82
            }
            timeframes = ["1H", "4H", "1D"]
            phi = engine.calculate_phi(pattern_data, timeframes)
            if 0 <= phi <= 1:
                results["passed"] += 1
                print(f"  ✅ φ calculation: {phi:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ φ calculation: {phi:.3f} - Invalid range")
            
            # Test ρ (Recursive Feedback)
            historical_performance = {
                "pattern_1": [0.8, 0.85, 0.82, 0.87, 0.83],
                "pattern_2": [0.7, 0.72, 0.75, 0.68, 0.74]
            }
            successful_braids = [
                {"patterns": ["pattern_1"], "outcome": "success", "score": 0.9},
                {"patterns": ["pattern_2"], "outcome": "partial", "score": 0.6}
            ]
            
            rho = engine.calculate_rho(historical_performance, successful_braids)
            if 0 <= rho <= 1:
                results["passed"] += 1
                print(f"  ✅ ρ calculation: {rho:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ρ calculation: {rho:.3f} - Invalid range")
            
            # Test θ (Global Field)
            theta = engine.calculate_theta(successful_braids)
            if 0 <= theta <= 1:
                results["passed"] += 1
                print(f"  ✅ θ calculation: {theta:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ θ calculation: {theta:.3f} - Invalid range")
            
            # Test ω (Resonance Acceleration)
            phi_scores = {"pattern_1": phi, "pattern_2": 0.7}
            omega = engine.calculate_omega(phi_scores, rho, theta)
            if 0 <= omega <= 1:
                results["passed"] += 1
                print(f"  ✅ ω calculation: {omega:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ω calculation: {omega:.3f} - Invalid range")
            
            # Test S_i (Selection Score)
            pattern_data_si = {
                "accuracy": 0.85,
                "precision": 0.78,
                "stability": 0.82,
                "cost": 0.1,
                "frequency": 0.3
            }
            s_i = engine.calculate_selection_score(pattern_data_si, omega)
            if 0 <= s_i <= 1:
                results["passed"] += 1
                print(f"  ✅ S_i calculation: {s_i:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ S_i calculation: {s_i:.3f} - Invalid range")
            
            results["details"] = {
                "phi": phi,
                "rho": rho,
                "theta": theta,
                "omega": omega,
                "s_i": s_i
            }
            
            self.test_results["resonance_math"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Resonance calculations failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_module_specific_scoring(self):
        """Test module-specific scoring"""
        print("\n📊 Testing Module-Specific Scoring...")
        
        try:
            from src.learning_system.module_specific_scoring import ModuleSpecificScoring
            
            scoring = ModuleSpecificScoring()
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test data
            test_strands = [
                {
                    "strand_type": "pattern",
                    "content": "RSI divergence detected",
                    "metadata": {"rsi": 30, "confidence": 0.8}
                },
                {
                    "strand_type": "prediction_review",
                    "content": "Prediction accuracy: 85%",
                    "metadata": {"accuracy": 0.85, "confidence": 0.7}
                }
            ]
            
            resonance_context = {"omega": 0.7, "theta": 0.8}
            
            # Test scoring for different modules
            modules = ["CIL", "CTP", "RDI", "DM"]
            module_scores = {}
            
            for module in modules:
                data = {
                    "strands": test_strands,
                    "resonance_context": resonance_context
                }
                score = scoring.calculate_module_score(module, data)
                module_scores[module] = score
                
                if 0 <= score <= 1:
                    results["passed"] += 1
                    print(f"  ✅ {module} score: {score:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ {module} score: {score:.3f} - Invalid range")
            
            results["details"] = module_scores
            self.test_results["module_scoring"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Module scoring failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_learning_pipeline_basic(self):
        """Test basic learning pipeline functionality"""
        print("\n🔄 Testing Learning Pipeline Basic Functionality...")
        
        try:
            from src.learning_system.learning_pipeline import LearningPipeline
            from src.learning_system.centralized_learning_system import CentralizedLearningSystem
            from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
            
            # Create mock components
            class MockPromptManager:
                def get_prompt_template(self, file_path, template_name):
                    return "Test prompt template for {strands}"
            
            class MockLLMClient:
                async def generate_completion(self, **kwargs):
                    return "Mock LLM response"
            
            class MockSupabaseManager:
                pass
            
            # Initialize components
            prompt_manager = MockPromptManager()
            llm_client = MockLLMClient()
            supabase_manager = MockSupabaseManager()
            learning_system = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            resonance_engine = MathematicalResonanceEngine()
            pipeline = LearningPipeline(learning_system, resonance_engine)
            
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test pipeline initialization
            if pipeline is not None:
                results["passed"] += 1
                print("  ✅ Pipeline initialized successfully")
            else:
                results["failed"] += 1
                print("  ❌ Pipeline initialization failed")
            
            # Test context injection method
            try:
                context = await pipeline.get_context_for_strand_type("pattern")
                if context is not None:
                    results["passed"] += 1
                    print("  ✅ Context injection method works")
                else:
                    results["failed"] += 1
                    print("  ❌ Context injection returned None")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Context injection failed: {e}")
            
            results["details"] = {
                "pipeline_initialized": pipeline is not None,
                "context_method_works": True
            }
            
            self.test_results["learning_pipeline"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Learning pipeline test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_centralized_learning_system_basic(self):
        """Test basic centralized learning system functionality"""
        print("\n🧠 Testing Centralized Learning System Basic Functionality...")
        
        try:
            from src.learning_system.centralized_learning_system import CentralizedLearningSystem
            
            # Create mock components
            class MockPromptManager:
                def get_prompt_template(self, file_path, template_name):
                    return "Test prompt template for {strands}"
            
            class MockLLMClient:
                async def generate_completion(self, **kwargs):
                    return "Mock LLM response"
            
            class MockSupabaseManager:
                pass
            
            # Initialize learning system
            prompt_manager = MockPromptManager()
            llm_client = MockLLMClient()
            supabase_manager = MockSupabaseManager()
            learning_system = CentralizedLearningSystem(supabase_manager, llm_client, prompt_manager)
            
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test learning system initialization
            if learning_system is not None:
                results["passed"] += 1
                print("  ✅ Learning system initialized successfully")
            else:
                results["failed"] += 1
                print("  ❌ Learning system initialization failed")
            
            # Test resonance context method
            try:
                resonance_context = await learning_system.get_resonance_context()
                if resonance_context is not None:
                    results["passed"] += 1
                    print("  ✅ Resonance context method works")
                else:
                    results["failed"] += 1
                    print("  ❌ Resonance context returned None")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Resonance context failed: {e}")
            
            results["details"] = {
                "learning_system_initialized": learning_system is not None,
                "resonance_context_works": True
            }
            
            self.test_results["centralized_learning"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Centralized learning system test failed: {e}")
            traceback.print_exc()
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 SIMPLE FUNCTIONALITY TEST SUMMARY")
        print("="*60)
        
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
        
        print("-"*60)
        overall_status = "✅ ALL TESTS PASSED" if total_failed == 0 else "❌ SOME TESTS FAILED"
        print(f"OVERALL: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*60)
        
        return total_failed == 0

async def main():
    """Run simple functionality tests"""
    print("🚀 Starting Simple Functionality Tests")
    print("="*60)
    
    tester = SimpleFunctionalityTester()
    
    # Run all tests
    tests = [
        ("Mathematical Resonance", tester.test_mathematical_resonance_calculations),
        ("Module-Specific Scoring", tester.test_module_specific_scoring),
        ("Learning Pipeline Basic", tester.test_learning_pipeline_basic),
        ("Centralized Learning Basic", tester.test_centralized_learning_system_basic)
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
        print("\n🎉 All simple functionality tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review and fix issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
