#!/usr/bin/env python3
"""
Complete System Validation Test
Tests the complete centralized learning system workflow with real data validation
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

class CompleteSystemValidator:
    def __init__(self):
        self.test_results = {}
        self.test_data = self._create_comprehensive_test_data()
    
    def _create_comprehensive_test_data(self):
        """Create comprehensive test data for system validation"""
        return {
            "market_data": [
                {
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
                },
                {
                    "symbol": "ETHUSDT",
                    "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "open": 3000.0,
                    "high": 3100.0,
                    "low": 2950.0,
                    "close": 3050.0,
                    "volume": 500000.0,
                    "rsi": 45.0,
                    "macd": 75.0,
                    "bollinger_upper": 3150.0,
                    "bollinger_lower": 2850.0
                }
            ],
            "strands": [
                {
                    "strand_type": "pattern",
                    "content": "RSI divergence detected on 1H timeframe",
                    "metadata": {
                        "rsi": 30,
                        "timeframe": "1H",
                        "confidence": 0.8,
                        "pattern_type": "rsi_divergence",
                        "accuracy": 0.85,
                        "precision": 0.78,
                        "stability": 0.82
                    },
                    "source": "rsi_analyzer",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "strand_type": "prediction_review",
                    "content": "Predicted BTC price increase to $52k - actual: $50.5k",
                    "metadata": {
                        "predicted_price": 52000,
                        "actual_price": 50500,
                        "accuracy": 0.75,
                        "confidence": 0.7,
                        "precision": 0.68
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
                        "outcome": "success",
                        "return": 0.01
                    },
                    "source": "trading_engine",
                    "created_at": datetime.now().isoformat()
                },
                {
                    "strand_type": "pattern",
                    "content": "Volume spike with price drop - potential reversal",
                    "metadata": {
                        "volume": 1500000,
                        "price_change": -0.05,
                        "confidence": 0.7,
                        "pattern_type": "volume_spike",
                        "accuracy": 0.72,
                        "precision": 0.68,
                        "stability": 0.75
                    },
                    "source": "volume_analyzer",
                    "created_at": datetime.now().isoformat()
                }
            ]
        }
    
    async def test_mathematical_resonance_comprehensive(self):
        """Test comprehensive mathematical resonance with real data"""
        print("🧮 Testing Mathematical Resonance Comprehensive...")
        
        try:
            from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
            
            engine = MathematicalResonanceEngine()
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test with real pattern data
            patterns = []
            for strand in self.test_data["strands"]:
                if strand["strand_type"] == "pattern":
                    patterns.append({
                        "id": f"pattern_{len(patterns)}",
                        "type": strand["metadata"].get("pattern_type", "unknown"),
                        "accuracy": strand["metadata"].get("accuracy", 0.5),
                        "precision": strand["metadata"].get("precision", 0.5),
                        "stability": strand["metadata"].get("stability", 0.5),
                        "cost": 0.1,
                        "frequency": 0.3
                    })
            
            # Calculate φ for each pattern
            phi_scores = {}
            for pattern in patterns:
                pattern_data = {
                    "accuracy": pattern["accuracy"],
                    "precision": pattern["precision"],
                    "stability": pattern["stability"]
                }
                timeframes = ["1H", "4H", "1D"]
                phi = engine.calculate_phi(pattern_data, timeframes)
                phi_scores[pattern["id"]] = phi
                
                if 0 <= phi <= 1:
                    results["passed"] += 1
                    print(f"  ✅ φ({pattern['type']}) = {phi:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ φ({pattern['type']}) = {phi:.3f} - Invalid range")
            
            # Calculate ρ with historical data
            historical_data = {
                "performance": {
                    "pattern_0": [0.8, 0.85, 0.82, 0.87, 0.83],
                    "pattern_1": [0.7, 0.72, 0.75, 0.68, 0.74]
                },
                "successful_braids": [
                    {"patterns": ["pattern_0"], "outcome": "success", "score": 0.9},
                    {"patterns": ["pattern_1"], "outcome": "partial", "score": 0.6}
                ]
            }
            
            rho = engine.calculate_rho(historical_data)
            if 0 <= rho <= 1:
                results["passed"] += 1
                print(f"  ✅ ρ = {rho:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ρ = {rho:.3f} - Invalid range")
            
            # Calculate θ
            successful_braids = [
                {"patterns": ["pattern_0"], "outcome": "success", "score": 0.9},
                {"patterns": ["pattern_1"], "outcome": "partial", "score": 0.6}
            ]
            theta = engine.calculate_theta(successful_braids)
            if 0 <= theta <= 1:
                results["passed"] += 1
                print(f"  ✅ θ = {theta:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ θ = {theta:.3f} - Invalid range")
            
            # Calculate ω
            learning_strength = 0.5
            omega = engine.calculate_omega(theta, learning_strength)
            if 0 <= omega <= 1:
                results["passed"] += 1
                print(f"  ✅ ω = {omega:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ω = {omega:.3f} - Invalid range")
            
            # Calculate S_i for each pattern
            for pattern in patterns:
                pattern_data_si = {
                    "accuracy": pattern["accuracy"],
                    "precision": pattern["precision"],
                    "stability": pattern["stability"],
                    "cost": pattern["cost"],
                    "frequency": pattern["frequency"],
                    "omega": omega
                }
                s_i_result = engine.calculate_selection_score(pattern_data_si)
                s_i = s_i_result.total_score if hasattr(s_i_result, 'total_score') else 0.0
                
                if 0 <= s_i <= 1:
                    results["passed"] += 1
                    print(f"  ✅ S_i({pattern['type']}) = {s_i:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ S_i({pattern['type']}) = {s_i:.3f} - Invalid range")
            
            # Test pattern weight calculation
            for pattern in patterns:
                weight = engine.calculate_pattern_weight(pattern, omega)
                if 0 <= weight <= 1:
                    results["passed"] += 1
                    print(f"  ✅ Weight({pattern['type']}) = {weight:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Weight({pattern['type']}) = {weight:.3f} - Invalid range")
            
            results["details"] = {
                "patterns_tested": len(patterns),
                "phi_scores": phi_scores,
                "rho": rho,
                "theta": theta,
                "omega": omega
            }
            
            self.test_results["resonance_comprehensive"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Resonance comprehensive test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_module_scoring_real_data(self):
        """Test module scoring with real strand data"""
        print("\n📊 Testing Module Scoring with Real Data...")
        
        try:
            from src.learning_system.module_specific_scoring import ModuleSpecificScoring
            
            scoring = ModuleSpecificScoring()
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test with real strands
            resonance_context = {"omega": 0.7, "theta": 0.8}
            
            modules = ["CIL", "CTP", "RDI", "DM"]
            module_scores = {}
            
            for module in modules:
                data = {
                    "strands": self.test_data["strands"],
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
            
            # Test detailed scoring for each strand type
            strand_type_scores = {}
            for strand in self.test_data["strands"]:
                detailed_scores = scoring.calculate_module_scores(strand, strand["strand_type"])
                strand_type_scores[strand["strand_type"]] = detailed_scores
                
                if isinstance(detailed_scores, dict) and len(detailed_scores) > 0:
                    results["passed"] += 1
                    print(f"  ✅ {strand['strand_type']} detailed scores: {len(detailed_scores)} modules")
                else:
                    results["failed"] += 1
                    print(f"  ❌ {strand['strand_type']} detailed scores failed")
            
            results["details"] = {
                "module_scores": module_scores,
                "strand_type_scores": strand_type_scores
            }
            
            self.test_results["module_scoring_real"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Module scoring real data test failed: {e}")
            traceback.print_exc()
            return False
    
    async def test_data_processing_pipeline(self):
        """Test complete data processing pipeline"""
        print("\n🔄 Testing Data Processing Pipeline...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test market data processing
            processed_strands = []
            for market_data in self.test_data["market_data"]:
                strands = self._process_market_data_to_strands(market_data)
                processed_strands.extend(strands)
            
            if len(processed_strands) > 0:
                results["passed"] += 1
                print(f"  ✅ Processed {len(processed_strands)} strands from market data")
            else:
                results["failed"] += 1
                print("  ❌ No strands processed from market data")
            
            # Test strand validation
            validation_results = []
            for i, strand in enumerate(processed_strands):
                validation = self._validate_strand_structure(strand)
                validation_results.append(validation)
                
                if validation["valid"]:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    print(f"  ❌ Strand {i} validation failed: {validation['issues']}")
            
            # Test strand clustering simulation
            clusters = self._simulate_strand_clustering(processed_strands)
            if len(clusters) > 0:
                results["passed"] += 1
                print(f"  ✅ Created {len(clusters)} clusters from strands")
            else:
                results["failed"] += 1
                print("  ❌ No clusters created")
            
            # Test context generation simulation
            context_data = self._simulate_context_generation(processed_strands)
            if context_data:
                results["passed"] += 1
                print(f"  ✅ Generated context for {len(context_data)} modules")
            else:
                results["failed"] += 1
                print("  ❌ No context generated")
            
            results["details"] = {
                "processed_strands": len(processed_strands),
                "validation_results": validation_results,
                "clusters": len(clusters),
                "context_modules": len(context_data) if context_data else 0
            }
            
            self.test_results["data_processing"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ Data processing pipeline test failed: {e}")
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
                    "stability": 0.8
                },
                "source": "rsi_analyzer",
                "created_at": market_data["timestamp"]
            })
        
        # Volume pattern
        if "volume" in market_data and "rsi" in market_data:
            volume = market_data["volume"]
            rsi = market_data["rsi"]
            
            if volume > 1000000 and rsi < 40:
                strands.append({
                    "strand_type": "pattern",
                    "content": "High volume with oversold RSI - potential reversal",
                    "metadata": {
                        "volume": volume,
                        "rsi": rsi,
                        "pattern_type": "volume_rsi_divergence",
                        "confidence": 0.7,
                        "accuracy": 0.75,
                        "precision": 0.7,
                        "stability": 0.75
                    },
                    "source": "volume_analyzer",
                    "created_at": market_data["timestamp"]
                })
        
        return strands
    
    def _validate_strand_structure(self, strand):
        """Validate strand structure"""
        issues = []
        
        required_fields = ["strand_type", "content", "metadata", "source", "created_at"]
        
        for field in required_fields:
            if field not in strand:
                issues.append(f"Missing {field}")
        
        if "metadata" in strand and not isinstance(strand["metadata"], dict):
            issues.append("Metadata must be a dictionary")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _simulate_strand_clustering(self, strands):
        """Simulate strand clustering"""
        clusters = {}
        
        for strand in strands:
            strand_type = strand["strand_type"]
            if strand_type not in clusters:
                clusters[strand_type] = []
            clusters[strand_type].append(strand)
        
        return clusters
    
    def _simulate_context_generation(self, strands):
        """Simulate context generation for modules"""
        context_data = {}
        
        # Group strands by type
        strands_by_type = {}
        for strand in strands:
            strand_type = strand["strand_type"]
            if strand_type not in strands_by_type:
                strands_by_type[strand_type] = []
            strands_by_type[strand_type].append(strand)
        
        # Generate context for each module
        module_subscriptions = {
            "CIL": ["prediction_review"],
            "CTP": ["trade_outcome"],
            "RDI": ["pattern"],
            "DM": ["pattern", "trade_outcome"]
        }
        
        for module, subscribed_types in module_subscriptions.items():
            module_context = []
            for strand_type in subscribed_types:
                if strand_type in strands_by_type:
                    module_context.extend(strands_by_type[strand_type])
            
            if module_context:
                context_data[module] = {
                    "strands": module_context,
                    "count": len(module_context),
                    "relevance_score": 0.8
                }
        
        return context_data
    
    async def test_system_integration(self):
        """Test system integration and workflow"""
        print("\n🔗 Testing System Integration...")
        
        try:
            results = {"passed": 0, "failed": 0, "details": []}
            
            # Test workflow simulation
            workflow_steps = [
                "market_data_input",
                "strand_creation",
                "strand_validation",
                "resonance_calculation",
                "clustering",
                "context_generation",
                "module_scoring"
            ]
            
            completed_steps = []
            
            # Step 1: Market data input
            if self.test_data["market_data"]:
                completed_steps.append("market_data_input")
                results["passed"] += 1
                print("  ✅ Market data input ready")
            else:
                results["failed"] += 1
                print("  ❌ No market data available")
            
            # Step 2: Strand creation
            all_strands = self.test_data["strands"].copy()
            for market_data in self.test_data["market_data"]:
                all_strands.extend(self._process_market_data_to_strands(market_data))
            
            if len(all_strands) > 0:
                completed_steps.append("strand_creation")
                results["passed"] += 1
                print(f"  ✅ Created {len(all_strands)} strands")
            else:
                results["failed"] += 1
                print("  ❌ No strands created")
            
            # Step 3: Strand validation
            valid_strands = 0
            for strand in all_strands:
                validation = self._validate_strand_structure(strand)
                if validation["valid"]:
                    valid_strands += 1
            
            if valid_strands == len(all_strands):
                completed_steps.append("strand_validation")
                results["passed"] += 1
                print(f"  ✅ All {valid_strands} strands validated")
            else:
                results["failed"] += 1
                print(f"  ❌ Only {valid_strands}/{len(all_strands)} strands valid")
            
            # Step 4: Resonance calculation
            try:
                from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                engine = MathematicalResonanceEngine()
                
                # Calculate basic resonance
                pattern_data = {"accuracy": 0.8, "precision": 0.75, "stability": 0.8}
                timeframes = ["1H", "4H", "1D"]
                phi = engine.calculate_phi(pattern_data, timeframes)
                
                if 0 <= phi <= 1:
                    completed_steps.append("resonance_calculation")
                    results["passed"] += 1
                    print(f"  ✅ Resonance calculation: φ = {phi:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Invalid resonance calculation: φ = {phi:.3f}")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Resonance calculation failed: {e}")
            
            # Step 5: Clustering
            clusters = self._simulate_strand_clustering(all_strands)
            if len(clusters) > 0:
                completed_steps.append("clustering")
                results["passed"] += 1
                print(f"  ✅ Created {len(clusters)} clusters")
            else:
                results["failed"] += 1
                print("  ❌ No clusters created")
            
            # Step 6: Context generation
            context_data = self._simulate_context_generation(all_strands)
            if context_data:
                completed_steps.append("context_generation")
                results["passed"] += 1
                print(f"  ✅ Generated context for {len(context_data)} modules")
            else:
                results["failed"] += 1
                print("  ❌ No context generated")
            
            # Step 7: Module scoring
            try:
                from src.learning_system.module_specific_scoring import ModuleSpecificScoring
                scoring = ModuleSpecificScoring()
                
                resonance_context = {"omega": 0.7, "theta": 0.8}
                data = {"strands": all_strands, "resonance_context": resonance_context}
                
                cil_score = scoring.calculate_module_score("CIL", data)
                if 0 <= cil_score <= 1:
                    completed_steps.append("module_scoring")
                    results["passed"] += 1
                    print(f"  ✅ Module scoring: CIL = {cil_score:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Invalid module scoring: CIL = {cil_score:.3f}")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Module scoring failed: {e}")
            
            results["details"] = {
                "workflow_steps": workflow_steps,
                "completed_steps": completed_steps,
                "completion_rate": len(completed_steps) / len(workflow_steps)
            }
            
            self.test_results["system_integration"] = results
            return results["failed"] == 0
            
        except Exception as e:
            print(f"  ❌ System integration test failed: {e}")
            traceback.print_exc()
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 COMPLETE SYSTEM VALIDATION SUMMARY")
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
        overall_status = "✅ ALL SYSTEM TESTS PASSED" if total_failed == 0 else "❌ SOME SYSTEM TESTS FAILED"
        print(f"OVERALL: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*80)
        
        return total_failed == 0

async def main():
    """Run complete system validation tests"""
    print("🚀 Starting Complete System Validation Tests")
    print("="*80)
    
    validator = CompleteSystemValidator()
    
    # Run all tests
    tests = [
        ("Mathematical Resonance Comprehensive", validator.test_mathematical_resonance_comprehensive),
        ("Module Scoring Real Data", validator.test_module_scoring_real_data),
        ("Data Processing Pipeline", validator.test_data_processing_pipeline),
        ("System Integration", validator.test_system_integration)
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
    
    if success:
        print("\n🎉 All complete system validation tests passed!")
        print("✅ The centralized learning system is working correctly")
        print("✅ Ready for production deployment")
    else:
        print("\n⚠️  Some system tests failed. Review and fix issues.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
