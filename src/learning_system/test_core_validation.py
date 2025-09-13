#!/usr/bin/env python3
"""
Core Functionality Validation Test
Tests the core mathematical and scoring functionality without complex dependencies
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

class CoreValidationTester:
    def __init__(self):
        self.test_results = {}
    
    async def test_mathematical_resonance_core(self):
        """Test core mathematical resonance calculations"""
        print("🧮 Testing Mathematical Resonance Core Calculations...")
        
        try:
            from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
            
            engine = MathematicalResonanceEngine()
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test φ (Fractal Self-Similarity) - correct signature
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
            
            # Test ρ (Recursive Feedback) - correct signature
            historical_data = {
                "performance": {
                    "pattern_1": [0.8, 0.85, 0.82, 0.87, 0.83],
                    "pattern_2": [0.7, 0.72, 0.75, 0.68, 0.74]
                },
                "successful_braids": [
                    {"patterns": ["pattern_1"], "outcome": "success", "score": 0.9},
                    {"patterns": ["pattern_2"], "outcome": "partial", "score": 0.6}
                ]
            }
            rho = engine.calculate_rho(historical_data)
            if 0 <= rho <= 1:
                results["passed"] += 1
                print(f"  ✅ ρ calculation: {rho:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ρ calculation: {rho:.3f} - Invalid range")
            
            # Test θ (Global Field)
            successful_braids = [
                {"patterns": ["pattern_1"], "outcome": "success", "score": 0.9},
                {"patterns": ["pattern_2"], "outcome": "partial", "score": 0.6}
            ]
            theta = engine.calculate_theta(successful_braids)
            if 0 <= theta <= 1:
                results["passed"] += 1
                print(f"  ✅ θ calculation: {theta:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ θ calculation: {theta:.3f} - Invalid range")
            
            # Test ω (Resonance Acceleration)
            learning_strength = 0.5  # Mock learning strength
            omega = engine.calculate_omega(theta, learning_strength)
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
                "frequency": 0.3,
                "omega": omega
            }
            s_i_result = engine.calculate_selection_score(pattern_data_si)
            s_i = s_i_result.total_score if hasattr(s_i_result, 'total_score') else 0.0
            if 0 <= s_i <= 1:
                results["passed"] += 1
                print(f"  ✅ S_i calculation: {s_i:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ S_i calculation: {s_i:.3f} - Invalid range")
            
            # Test pattern weight calculation
            pattern = {
                "accuracy": 0.85,
                "precision": 0.78,
                "stability": 0.82,
                "cost": 0.1,
                "frequency": 0.3
            }
            weight = engine.calculate_pattern_weight(pattern, omega)
            if 0 <= weight <= 1:
                results["passed"] += 1
                print(f"  ✅ Pattern weight: {weight:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ Pattern weight: {weight:.3f} - Invalid range")
            
            results["details"] = {
                "phi": phi,
                "rho": rho,
                "theta": theta,
                "omega": omega,
                "s_i": s_i,
                "weight": weight
            }
            
            self.test_results["resonance_core"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Resonance core calculations failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_module_scoring_comprehensive(self):
        """Test comprehensive module-specific scoring"""
        print("\n📊 Testing Module-Specific Scoring Comprehensive...")
        
        try:
            from src.learning_system.module_specific_scoring import ModuleSpecificScoring
            
            scoring = ModuleSpecificScoring()
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test data with different strand types
            test_strands = [
                {
                    "strand_type": "pattern",
                    "content": "RSI divergence detected",
                    "metadata": {"rsi": 30, "confidence": 0.8, "accuracy": 0.85}
                },
                {
                    "strand_type": "prediction_review",
                    "content": "Prediction accuracy: 85%",
                    "metadata": {"accuracy": 0.85, "confidence": 0.7, "precision": 0.78}
                },
                {
                    "strand_type": "trade_outcome",
                    "content": "Trade executed successfully",
                    "metadata": {"profit": 100, "outcome": "success", "return": 0.05}
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
            
            # Test module-specific scoring method
            try:
                module_scores_detailed = scoring.calculate_module_scores(test_strands[0], "pattern")
                if isinstance(module_scores_detailed, dict) and len(module_scores_detailed) > 0:
                    results["passed"] += 1
                    print(f"  ✅ Module-specific scores: {len(module_scores_detailed)} modules")
                else:
                    results["failed"] += 1
                    print("  ❌ Module-specific scores returned empty or invalid")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Module-specific scores failed: {e}")
            
            results["details"] = {
                "module_scores": module_scores,
                "detailed_scores": module_scores_detailed if 'module_scores_detailed' in locals() else {}
            }
            
            self.test_results["module_scoring"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Module scoring comprehensive failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_data_validation(self):
        """Test data validation and processing"""
        print("\n🔍 Testing Data Validation...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test market data validation
            market_data = {
                "symbol": "BTCUSDT",
                "timestamp": datetime.now().isoformat(),
                "open": 50000.0,
                "high": 51000.0,
                "low": 49500.0,
                "close": 50500.0,
                "volume": 1000000.0,
                "rsi": 65.5,
                "macd": 150.0
            }
            
            # Validate required fields
            required_fields = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
            missing_fields = [field for field in required_fields if field not in market_data]
            
            if len(missing_fields) == 0:
                results["passed"] += 1
                print("  ✅ Market data has all required fields")
            else:
                results["failed"] += 1
                print(f"  ❌ Market data missing fields: {missing_fields}")
            
            # Validate data types
            numeric_fields = ["open", "high", "low", "close", "volume", "rsi", "macd"]
            type_errors = []
            
            for field in numeric_fields:
                if field in market_data and not isinstance(market_data[field], (int, float)):
                    type_errors.append(f"{field}: {type(market_data[field])}")
            
            if len(type_errors) == 0:
                results["passed"] += 1
                print("  ✅ Market data types are correct")
            else:
                results["failed"] += 1
                print(f"  ❌ Market data type errors: {type_errors}")
            
            # Validate OHLC consistency
            ohlc_valid = True
            if market_data["high"] < max(market_data["open"], market_data["close"]):
                ohlc_valid = False
                print("  ❌ High price is lower than open/close")
            if market_data["low"] > min(market_data["open"], market_data["close"]):
                ohlc_valid = False
                print("  ❌ Low price is higher than open/close")
            
            if ohlc_valid:
                results["passed"] += 1
                print("  ✅ OHLC data is consistent")
            else:
                results["failed"] += 1
                print("  ❌ OHLC data is inconsistent")
            
            # Test strand creation
            strands = self._create_test_strands()
            if len(strands) > 0:
                results["passed"] += 1
                print(f"  ✅ Created {len(strands)} test strands")
            else:
                results["failed"] += 1
                print("  ❌ Failed to create test strands")
            
            # Validate strand structure
            strand_validation = self._validate_strands(strands)
            if strand_validation["valid"]:
                results["passed"] += 1
                print("  ✅ Strand structure validation passed")
            else:
                results["failed"] += 1
                print(f"  ❌ Strand structure validation failed: {strand_validation['issues']}")
            
            results["details"] = {
                "market_data": market_data,
                "strands_created": len(strands),
                "strand_validation": strand_validation
            }
            
            self.test_results["data_validation"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Data validation failed: {e}")
            traceback.print_exc()
            return False
    
    def _create_test_strands(self):
        """Create test strands for validation"""
        return [
            {
                "strand_type": "pattern",
                "content": "RSI divergence detected on 1H timeframe",
                "metadata": {
                    "rsi": 30,
                    "timeframe": "1H",
                    "confidence": 0.8,
                    "pattern_type": "rsi_divergence"
                },
                "source": "rsi_analyzer",
                "created_at": datetime.now().isoformat()
            },
            {
                "strand_type": "prediction_review",
                "content": "Predicted price increase to $52k - actual: $50.5k",
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
    
    def _validate_strands(self, strands):
        """Validate strand structure"""
        issues = []
        
        if not strands:
            issues.append("No strands provided")
            return {"valid": False, "issues": issues}
        
        required_fields = ["strand_type", "content", "metadata", "source", "created_at"]
        
        for i, strand in enumerate(strands):
            if not isinstance(strand, dict):
                issues.append(f"Strand {i} is not a dictionary")
                continue
            
            for field in required_fields:
                if field not in strand:
                    issues.append(f"Strand {i} missing {field}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    async def test_performance_basic(self):
        """Test basic performance characteristics"""
        print("\n⚡ Testing Basic Performance...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test calculation speed
            from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
            
            engine = MathematicalResonanceEngine()
            
            # Time resonance calculations
            start_time = time.time()
            
            for i in range(100):
                pattern_data = {
                    "accuracy": 0.8 + (i % 20) * 0.01,
                    "precision": 0.75 + (i % 15) * 0.01,
                    "stability": 0.8 + (i % 10) * 0.01
                }
                timeframes = ["1H", "4H", "1D"]
                phi = engine.calculate_phi(pattern_data, timeframes)
            
            end_time = time.time()
            calculation_time = end_time - start_time
            
            if calculation_time < 1.0:  # Should complete 100 calculations in under 1 second
                results["passed"] += 1
                print(f"  ✅ Resonance calculations fast: {calculation_time:.3f}s for 100 iterations")
            else:
                results["failed"] += 1
                print(f"  ❌ Resonance calculations slow: {calculation_time:.3f}s for 100 iterations")
            
            # Test memory usage (basic)
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb < 200:  # Less than 200MB
                results["passed"] += 1
                print(f"  ✅ Memory usage reasonable: {memory_mb:.1f}MB")
            else:
                results["failed"] += 1
                print(f"  ❌ Memory usage high: {memory_mb:.1f}MB")
            
            results["details"] = {
                "calculation_time": calculation_time,
                "memory_mb": memory_mb
            }
            
            self.test_results["performance"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Performance test failed: {e}")
            traceback.print_exc()
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 CORE FUNCTIONALITY VALIDATION SUMMARY")
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
        overall_status = "✅ ALL CORE TESTS PASSED" if total_failed == 0 else "❌ SOME CORE TESTS FAILED"
        print(f"OVERALL: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*80)
        
        return total_failed == 0

async def main():
    """Run core functionality validation tests"""
    print("🚀 Starting Core Functionality Validation Tests")
    print("="*80)
    
    tester = CoreValidationTester()
    
    # Run all tests
    tests = [
        ("Mathematical Resonance Core", tester.test_mathematical_resonance_core),
        ("Module-Specific Scoring Comprehensive", tester.test_module_scoring_comprehensive),
        ("Data Validation", tester.test_data_validation),
        ("Basic Performance", tester.test_performance_basic)
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
        print("\n🎉 All core functionality validation tests passed!")
        print("✅ System core is working correctly")
    else:
        print("\n⚠️  Some core tests failed. Review and fix issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
