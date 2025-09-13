#!/usr/bin/env python3
"""
Real Workflow Validation Test
Tests the complete system workflow with real data and validates outputs
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

from src.learning_system.centralized_learning_system import CentralizedLearningSystem
from src.learning_system.learning_pipeline import LearningPipeline
from src.learning_system.context_injection_engine import ContextInjectionEngine
from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
from src.learning_system.module_specific_scoring import ModuleSpecificScoring
from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
from Modules.Alpha_Detector.src.database.supabase_client import SupabaseClient

class RealWorkflowValidator:
    def __init__(self):
        self.llm_client = None
        self.prompt_manager = None
        self.learning_system = None
        self.pipeline = None
        self.context_engine = None
        self.resonance_engine = None
        self.scoring = None
        self.db_client = None
        self.test_results = {}
        
    async def setup(self):
        """Initialize all components"""
        print("🔧 Setting up real workflow validation...")
        
        try:
            self.llm_client = OpenRouterClient()
            self.prompt_manager = PromptManager()
            self.learning_system = CentralizedLearningSystem(self.prompt_manager)
            self.resonance_engine = MathematicalResonanceEngine()
            self.pipeline = LearningPipeline(self.learning_system, self.resonance_engine)
            self.context_engine = ContextInjectionEngine(self.learning_system)
            self.scoring = ModuleSpecificScoring()
            self.db_client = SupabaseClient()
            
            print("✅ All components initialized")
            return True
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def test_market_data_processing(self):
        """Test market data processing with real data"""
        print("\n📊 Testing Market Data Processing...")
        
        # Create realistic market data
        market_data = {
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
            "bollinger_lower": 48000.0,
            "vwap": 50250.0,
            "atr": 500.0
        }
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test data validation
            validation_result = self._validate_market_data(market_data)
            if validation_result["valid"]:
                results["passed"] += 1
                print("  ✅ Market data validation passed")
            else:
                results["failed"] += 1
                print(f"  ❌ Market data validation failed: {validation_result['issues']}")
            
            # Test strand creation from market data
            strands = self._create_strands_from_market_data(market_data)
            if len(strands) > 0:
                results["passed"] += 1
                print(f"  ✅ Created {len(strands)} strands from market data")
            else:
                results["failed"] += 1
                print("  ❌ Failed to create strands from market data")
            
            # Test strand storage
            stored_strands = []
            for strand in strands:
                try:
                    result = await self.db_client.store_strand(strand)
                    if result:
                        stored_strands.append(result)
                        results["passed"] += 1
                    else:
                        results["failed"] += 1
                except Exception as e:
                    results["failed"] += 1
                    print(f"    ❌ Failed to store strand: {e}")
            
            if len(stored_strands) > 0:
                print(f"  ✅ Stored {len(stored_strands)} strands in database")
            else:
                print("  ❌ No strands stored")
            
            results["details"] = {
                "market_data": market_data,
                "strands_created": len(strands),
                "strands_stored": len(stored_strands),
                "validation": validation_result
            }
            
        except Exception as e:
            results["failed"] += 1
            print(f"  ❌ Market data processing failed: {e}")
            traceback.print_exc()
        
        self.test_results["market_data_processing"] = results
        return results["failed"] == 0
    
    def _validate_market_data(self, data: Dict) -> Dict:
        """Validate market data structure and values"""
        required_fields = ["symbol", "timestamp", "open", "high", "low", "close", "volume"]
        issues = []
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                issues.append(f"Missing required field: {field}")
        
        # Check data types and ranges
        if "open" in data and not isinstance(data["open"], (int, float)):
            issues.append("Open price must be numeric")
        elif "open" in data and data["open"] <= 0:
            issues.append("Open price must be positive")
        
        if "volume" in data and not isinstance(data["volume"], (int, float)):
            issues.append("Volume must be numeric")
        elif "volume" in data and data["volume"] < 0:
            issues.append("Volume must be non-negative")
        
        # Check OHLC consistency
        if all(field in data for field in ["open", "high", "low", "close"]):
            if data["high"] < max(data["open"], data["close"]):
                issues.append("High price is lower than open/close")
            if data["low"] > min(data["open"], data["close"]):
                issues.append("Low price is higher than open/close")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _create_strands_from_market_data(self, market_data: Dict) -> List[Dict]:
        """Create strands from market data"""
        strands = []
        
        # RSI pattern strand
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
                    "timeframe": "1H"
                },
                "source": "rsi_analyzer",
                "created_at": datetime.now().isoformat()
            })
        
        # Volume pattern strand
        if "volume" in market_data and "rsi" in market_data:
            volume = market_data["volume"]
            rsi = market_data["rsi"]
            
            if volume > 1000000 and rsi < 40:  # High volume with low RSI
                strands.append({
                    "strand_type": "pattern",
                    "content": "High volume with oversold RSI - potential reversal",
                    "metadata": {
                        "volume": volume,
                        "rsi": rsi,
                        "pattern_type": "volume_rsi_divergence",
                        "confidence": 0.7
                    },
                    "source": "volume_analyzer",
                    "created_at": datetime.now().isoformat()
                })
        
        # Price movement strand
        if all(field in market_data for field in ["open", "close", "high", "low"]):
            price_change = (market_data["close"] - market_data["open"]) / market_data["open"]
            volatility = (market_data["high"] - market_data["low"]) / market_data["open"]
            
            if abs(price_change) > 0.02:  # >2% move
                direction = "bullish" if price_change > 0 else "bearish"
                strands.append({
                    "strand_type": "pattern",
                    "content": f"Significant {direction} price movement: {price_change:.2%}",
                    "metadata": {
                        "price_change": price_change,
                        "volatility": volatility,
                        "direction": direction,
                        "confidence": 0.6
                    },
                    "source": "price_analyzer",
                    "created_at": datetime.now().isoformat()
                })
        
        return strands
    
    async def test_learning_pipeline_processing(self):
        """Test learning pipeline with real strands"""
        print("\n🔄 Testing Learning Pipeline Processing...")
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Get recent strands from database
            recent_strands = await self._get_recent_strands(limit=10)
            
            if not recent_strands:
                # Create test strands if none exist
                test_strands = self._create_test_strands()
                for strand in test_strands:
                    await self.db_client.store_strand(strand)
                recent_strands = test_strands
                print("  📝 Created test strands for processing")
            
            print(f"  📊 Processing {len(recent_strands)} strands through learning pipeline")
            
            # Process strands through pipeline
            processed_strands = await self.pipeline.process_strands(recent_strands)
            
            if processed_strands and len(processed_strands) > 0:
                results["passed"] += 1
                print(f"  ✅ Successfully processed {len(processed_strands)} strands")
                
                # Validate processed strands
                validation_result = self._validate_processed_strands(processed_strands)
                if validation_result["valid"]:
                    results["passed"] += 1
                    print("  ✅ Processed strands validation passed")
                else:
                    results["failed"] += 1
                    print(f"  ❌ Processed strands validation failed: {validation_result['issues']}")
            else:
                results["failed"] += 1
                print("  ❌ No strands processed by pipeline")
            
            # Test clustering
            try:
                clusters = await self.pipeline.get_strand_clusters(recent_strands)
                if clusters and len(clusters) > 0:
                    results["passed"] += 1
                    print(f"  ✅ Created {len(clusters)} clusters")
                else:
                    results["failed"] += 1
                    print("  ❌ No clusters created")
            except Exception as e:
                results["failed"] += 1
                print(f"  ❌ Clustering failed: {e}")
            
            results["details"] = {
                "input_strands": len(recent_strands),
                "processed_strands": len(processed_strands) if processed_strands else 0,
                "clusters": len(clusters) if 'clusters' in locals() and clusters else 0
            }
            
        except Exception as e:
            results["failed"] += 1
            print(f"  ❌ Learning pipeline processing failed: {e}")
            traceback.print_exc()
        
        self.test_results["learning_pipeline"] = results
        return results["failed"] == 0
    
    def _create_test_strands(self) -> List[Dict]:
        """Create test strands for processing"""
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
    
    async def _get_recent_strands(self, limit: int = 10) -> List[Dict]:
        """Get recent strands from database"""
        try:
            # This would be implemented based on your database client
            # For now, return empty list
            return []
        except Exception as e:
            print(f"  ⚠️  Could not fetch recent strands: {e}")
            return []
    
    def _validate_processed_strands(self, strands: List[Dict]) -> Dict:
        """Validate processed strands"""
        issues = []
        
        if not strands:
            issues.append("No strands provided")
            return {"valid": False, "issues": issues}
        
        for i, strand in enumerate(strands):
            if not isinstance(strand, dict):
                issues.append(f"Strand {i} is not a dictionary")
                continue
            
            if "strand_type" not in strand:
                issues.append(f"Strand {i} missing strand_type")
            
            if "content" not in strand:
                issues.append(f"Strand {i} missing content")
            
            if "metadata" not in strand:
                issues.append(f"Strand {i} missing metadata")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    async def test_context_injection_quality(self):
        """Test context injection with real data"""
        print("\n💉 Testing Context Injection Quality...")
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Test CIL context injection
            cil_context = await self.context_engine.get_context_for_module(
                "CIL",
                ["prediction_review"]
            )
            
            if cil_context and len(cil_context) > 0:
                results["passed"] += 1
                print(f"  ✅ CIL context: {len(cil_context)} insights")
                
                # Validate context quality
                context_validation = self._validate_context_quality(cil_context, "CIL")
                if context_validation["valid"]:
                    results["passed"] += 1
                    print("  ✅ CIL context quality validation passed")
                else:
                    results["failed"] += 1
                    print(f"  ❌ CIL context quality failed: {context_validation['issues']}")
            else:
                results["failed"] += 1
                print("  ❌ No CIL context generated")
            
            # Test CTP context injection
            ctp_context = await self.context_engine.get_context_for_module(
                "CTP",
                ["trade_outcome"]
            )
            
            if ctp_context and len(ctp_context) > 0:
                results["passed"] += 1
                print(f"  ✅ CTP context: {len(ctp_context)} insights")
                
                # Validate context quality
                context_validation = self._validate_context_quality(ctp_context, "CTP")
                if context_validation["valid"]:
                    results["passed"] += 1
                    print("  ✅ CTP context quality validation passed")
                else:
                    results["failed"] += 1
                    print(f"  ❌ CTP context quality failed: {context_validation['issues']}")
            else:
                results["failed"] += 1
                print("  ❌ No CTP context generated")
            
            results["details"] = {
                "cil_context_count": len(cil_context) if cil_context else 0,
                "ctp_context_count": len(ctp_context) if ctp_context else 0
            }
            
        except Exception as e:
            results["failed"] += 1
            print(f"  ❌ Context injection failed: {e}")
            traceback.print_exc()
        
        self.test_results["context_injection"] = results
        return results["failed"] == 0
    
    def _validate_context_quality(self, context: List[Dict], module: str) -> Dict:
        """Validate context quality for a module"""
        issues = []
        
        if not context:
            issues.append("Empty context")
            return {"valid": False, "issues": issues}
        
        for i, insight in enumerate(context):
            if not isinstance(insight, dict):
                issues.append(f"Insight {i} is not a dictionary")
                continue
            
            if "content" not in insight:
                issues.append(f"Insight {i} missing content")
            
            if "relevance_score" not in insight:
                issues.append(f"Insight {i} missing relevance_score")
            elif not isinstance(insight["relevance_score"], (int, float)):
                issues.append(f"Insight {i} relevance_score is not numeric")
            elif not 0 <= insight["relevance_score"] <= 1:
                issues.append(f"Insight {i} relevance_score out of range")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    async def test_resonance_calculations_real_data(self):
        """Test resonance calculations with real data"""
        print("\n🧮 Testing Resonance Calculations with Real Data...")
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        try:
            # Create realistic pattern data
            patterns = [
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
                }
            ]
            
            # Test φ calculations
            phi_scores = {}
            for pattern in patterns:
                phi = self.resonance_engine.calculate_phi(
                    pattern["accuracy"],
                    pattern["precision"],
                    pattern["stability"]
                )
                phi_scores[pattern["id"]] = phi
                
                if 0 <= phi <= 1:
                    results["passed"] += 1
                    print(f"  ✅ φ({pattern['id']}) = {phi:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ φ({pattern['id']}) = {phi:.3f} - Invalid range")
            
            # Test ρ calculation
            historical_performance = {
                "pattern_1": [0.8, 0.85, 0.82, 0.87, 0.83],
                "pattern_2": [0.7, 0.72, 0.75, 0.68, 0.74]
            }
            
            successful_braids = [
                {"patterns": ["pattern_1"], "outcome": "success", "score": 0.9},
                {"patterns": ["pattern_2"], "outcome": "partial", "score": 0.6}
            ]
            
            rho = self.resonance_engine.calculate_rho(
                historical_performance,
                successful_braids
            )
            
            if 0 <= rho <= 1:
                results["passed"] += 1
                print(f"  ✅ ρ = {rho:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ρ = {rho:.3f} - Invalid range")
            
            # Test θ calculation
            theta = self.resonance_engine.calculate_theta(successful_braids)
            
            if 0 <= theta <= 1:
                results["passed"] += 1
                print(f"  ✅ θ = {theta:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ θ = {theta:.3f} - Invalid range")
            
            # Test ω calculation
            omega = self.resonance_engine.calculate_omega(phi_scores, rho, theta)
            
            if 0 <= omega <= 1:
                results["passed"] += 1
                print(f"  ✅ ω = {omega:.3f}")
            else:
                results["failed"] += 1
                print(f"  ❌ ω = {omega:.3f} - Invalid range")
            
            # Test S_i calculations
            for pattern in patterns:
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
                    print(f"  ✅ S_i({pattern['id']}) = {s_i:.3f}")
                else:
                    results["failed"] += 1
                    print(f"  ❌ S_i({pattern['id']}) = {s_i:.3f} - Invalid range")
            
            results["details"] = {
                "phi_scores": phi_scores,
                "rho": rho,
                "theta": theta,
                "omega": omega
            }
            
        except Exception as e:
            results["failed"] += 1
            print(f"  ❌ Resonance calculations failed: {e}")
            traceback.print_exc()
        
        self.test_results["resonance_calculations"] = results
        return results["failed"] == 0
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📊 REAL WORKFLOW VALIDATION SUMMARY")
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
    """Run real workflow validation tests"""
    print("🚀 Starting Real Workflow Validation Tests")
    print("="*80)
    
    validator = RealWorkflowValidator()
    
    # Setup
    if not await validator.setup():
        print("❌ Setup failed, cannot run tests")
        return False
    
    # Run all tests
    tests = [
        ("Market Data Processing", validator.test_market_data_processing),
        ("Learning Pipeline Processing", validator.test_learning_pipeline_processing),
        ("Context Injection Quality", validator.test_context_injection_quality),
        ("Resonance Calculations", validator.test_resonance_calculations_real_data)
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
        print("\n🎉 All real workflow validation tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review and fix issues before deployment.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
